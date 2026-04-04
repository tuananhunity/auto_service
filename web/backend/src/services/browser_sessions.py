from __future__ import annotations

import os
import platform
import secrets
import signal
import subprocess
import time
from datetime import timedelta
from pathlib import Path

from flask import current_app

from ..extensions import db
from ..models import BrowserSession, Job, User
from ..models.base import utcnow
from ..utils.paths import browser_profile_path, ensure_storage_tree
from .event_bus import emit_browser_session_update, emit_status


ACTIVE_SESSION_STATUSES = {"starting", "ready", "busy"}


class BrowserSessionManager:
    def open_for_user(self, user: User) -> BrowserSession:
        self._ensure_linux_runtime()
        ensure_storage_tree()

        existing = (
            BrowserSession.query.filter(
                BrowserSession.user_id == user.id,
                BrowserSession.status.in_(ACTIVE_SESSION_STATUSES),
            )
            .order_by(BrowserSession.created_at.desc())
            .first()
        )
        if existing:
            raise ValueError("User already has an active browser session.")

        session = BrowserSession(
            user_id=user.id,
            status="starting",
            display_number=self._next_value(BrowserSession.display_number, current_app.config["XVFB_START_DISPLAY"]),
            vnc_port=self._next_value(BrowserSession.vnc_port, current_app.config["VNC_PORT_START"]),
            debug_port=self._next_value(BrowserSession.debug_port, current_app.config["DEBUG_PORT_START"]),
            novnc_token=secrets.token_urlsafe(18),
            profile_path=str(browser_profile_path(user.id)),
            last_seen_at=utcnow(),
        )
        db.session.add(session)
        db.session.commit()

        try:
            self._launch_runtime(session)
            session.status = "ready"
            session.last_error = None
            session.last_seen_at = utcnow()
            db.session.commit()
        except Exception as exc:
            self._terminate_runtime(session)
            session.status = "failed"
            session.last_error = str(exc)
            db.session.commit()
            raise
        finally:
            self._refresh_token_file()
            emit_browser_session_update(user.id, session.to_dict())
            emit_status(user.id, self.status_payload(user.id))

        return session

    def close_for_user(self, user: User, session_id: int) -> BrowserSession:
        session = BrowserSession.query.filter_by(id=session_id, user_id=user.id).first_or_404()
        active_job = Job.query.filter(
            Job.browser_session_id == session.id,
            Job.status.in_(["starting", "running", "stopping"]),
        ).first()
        if active_job:
            raise ValueError("Stop the active job before closing this browser session.")
        self._terminate_runtime(session)
        session.status = "stopped"
        session.last_seen_at = utcnow()
        db.session.commit()
        self._refresh_token_file()
        emit_browser_session_update(user.id, session.to_dict())
        emit_status(user.id, self.status_payload(user.id))
        return session

    def get_for_user(self, user: User, session_id: int) -> BrowserSession:
        session = BrowserSession.query.filter_by(id=session_id, user_id=user.id).first_or_404()
        self.sync_health(session)
        session.last_seen_at = utcnow()
        db.session.commit()
        return session

    def latest_for_user(self, user: User) -> BrowserSession | None:
        session = (
            BrowserSession.query.filter_by(user_id=user.id)
            .order_by(BrowserSession.created_at.desc())
            .first()
        )
        if session:
            self.sync_health(session)
            session.last_seen_at = utcnow()
            db.session.commit()
        return session

    def novnc_url(self, session: BrowserSession) -> str | None:
        if session.status not in ACTIVE_SESSION_STATUSES:
            return None
        base = current_app.config["NOVNC_BASE_URL"].rstrip("/")
        return f"{base}/vnc.html?autoconnect=true&resize=remote&path=websockify?token={session.novnc_token}"

    def status_payload(self, user_id: int) -> dict:
        browser_session = (
            BrowserSession.query.filter(
                BrowserSession.user_id == user_id,
                BrowserSession.status.in_(ACTIVE_SESSION_STATUSES),
            )
            .order_by(BrowserSession.created_at.desc())
            .first()
        )
        active_job = (
            Job.query.filter(
                Job.user_id == user_id,
                Job.status.in_(["starting", "running", "stopping"]),
            )
            .order_by(Job.created_at.desc())
            .first()
        )
        return {
            "browser_session": browser_session.to_dict() if browser_session else None,
            "active_job": active_job.to_dict() if active_job else None,
        }

    def sync_health(self, session: BrowserSession) -> None:
        if session.status not in ACTIVE_SESSION_STATUSES:
            return
        if self._is_idle_expired(session):
            self._terminate_runtime(session)
            session.status = "stopped"
            session.last_error = "Browser session expired due to inactivity."
            session.last_seen_at = utcnow()
            db.session.commit()
            self._refresh_token_file()
            emit_browser_session_update(session.user_id, session.to_dict())
            emit_status(session.user_id, self.status_payload(session.user_id))
            return
        pid_values = [session.chrome_pid, session.x11vnc_pid, session.xvfb_pid]
        if not all(pid_values) or not all(self._pid_alive(pid) for pid in pid_values):
            session.status = "failed"
            session.last_error = "One or more runtime processes exited unexpectedly."
            session.last_seen_at = utcnow()
            db.session.commit()
            self._refresh_token_file()
            emit_browser_session_update(session.user_id, session.to_dict())
            emit_status(session.user_id, self.status_payload(session.user_id))

    def _launch_runtime(self, session: BrowserSession) -> None:
        runtime_dir = Path(current_app.config["BASE_STORAGE_DIR"]) / "runtime" / str(session.id)
        runtime_dir.mkdir(parents=True, exist_ok=True)

        xvfb_process = subprocess.Popen(
            [
                current_app.config["XVFB_BINARY"],
                f":{session.display_number}",
                "-screen",
                "0",
                "1440x900x24",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1)

        x11vnc_process = subprocess.Popen(
            [
                current_app.config["X11VNC_BINARY"],
                "-display",
                f":{session.display_number}",
                "-rfbport",
                str(session.vnc_port),
                "-forever",
                "-shared",
                "-localhost",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        env = os.environ.copy()
        env["DISPLAY"] = f":{session.display_number}"

        chrome_process = subprocess.Popen(
            [
                current_app.config["CHROME_BINARY_PATH"],
                f"--user-data-dir={session.profile_path}",
                f"--remote-debugging-port={session.debug_port}",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--window-size=1440,900",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )

        session.xvfb_pid = xvfb_process.pid
        session.x11vnc_pid = x11vnc_process.pid
        session.chrome_pid = chrome_process.pid
        db.session.commit()

        if not all(self._pid_alive(pid) for pid in [session.xvfb_pid, session.x11vnc_pid, session.chrome_pid]):
            raise RuntimeError("Failed to launch the browser runtime.")

    def _terminate_runtime(self, session: BrowserSession) -> None:
        for pid in [session.chrome_pid, session.x11vnc_pid, session.xvfb_pid]:
            if pid and self._pid_alive(pid):
                try:
                    os.killpg(pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
        session.chrome_pid = None
        session.x11vnc_pid = None
        session.xvfb_pid = None

    def _next_value(self, column, start_value: int) -> int:
        max_used = db.session.query(db.func.max(column)).scalar()
        return max(start_value, (max_used or 0) + 1)

    def _refresh_token_file(self) -> None:
        token_file = Path(current_app.config["NOVNC_TOKEN_FILE"])
        token_file.parent.mkdir(parents=True, exist_ok=True)
        active_sessions = BrowserSession.query.filter(
            BrowserSession.status.in_(ACTIVE_SESSION_STATUSES)
        ).all()
        lines = [f"{item.novnc_token}: 127.0.0.1:{item.vnc_port}" for item in active_sessions]
        token_file.write_text("\n".join(lines), encoding="utf-8")

    def _pid_alive(self, pid: int | None) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _ensure_linux_runtime(self) -> None:
        if platform.system().lower() != "linux":
            raise RuntimeError("Remote browser runtime is implemented for Linux hosts only.")

    def _is_idle_expired(self, session: BrowserSession) -> bool:
        active_job = Job.query.filter(
            Job.browser_session_id == session.id,
            Job.status.in_(["starting", "running", "stopping"]),
        ).first()
        if active_job:
            return False
        ttl = timedelta(minutes=current_app.config["BROWSER_IDLE_TTL_MINUTES"])
        return session.last_seen_at < (utcnow() - ttl)
