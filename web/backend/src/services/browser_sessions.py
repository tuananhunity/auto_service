from __future__ import annotations

import secrets
from datetime import timedelta
from pathlib import Path

from flask import current_app

from ..extensions import db
from ..models import BrowserSession, Job, User
from ..models.base import utcnow
from ..utils.paths import ensure_storage_tree
from .browser_runtime import LinuxRemoteBrowserRuntime, WindowsLocalChromeRuntime
from .event_bus import emit_browser_session_update, emit_status


ACTIVE_SESSION_STATUSES = {"starting", "ready", "busy"}


class BrowserSessionManager:
    def open_for_user(self, user: User) -> BrowserSession:
        ensure_storage_tree()
        runtime = self._runtime()

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
            runtime_mode=runtime.runtime_mode,
            viewer_type=runtime.viewer_type,
            display_number=self._next_value(BrowserSession.display_number, current_app.config["XVFB_START_DISPLAY"])
            if runtime.runtime_mode == "linux_remote"
            else None,
            vnc_port=self._next_value(BrowserSession.vnc_port, current_app.config["VNC_PORT_START"])
            if runtime.runtime_mode == "linux_remote"
            else None,
            debug_port=self._next_value(BrowserSession.debug_port, current_app.config["DEBUG_PORT_START"]),
            novnc_token=secrets.token_urlsafe(18) if runtime.runtime_mode == "linux_remote" else None,
            profile_path="",
            last_seen_at=utcnow(),
        )
        runtime.prepare_session(session)
        db.session.add(session)
        db.session.commit()

        try:
            runtime.launch(session)
            session.status = "ready"
            session.last_error = None
            session.viewer_url = runtime.viewer_url(session)
            session.last_seen_at = utcnow()
            db.session.commit()
        except Exception as exc:
            runtime.terminate(session)
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
        self._runtime_for_session(session).terminate(session)
        session.status = "stopped"
        session.last_seen_at = utcnow()
        session.viewer_url = None if session.runtime_mode == "linux_remote" else session.viewer_url
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
        if session.status not in ACTIVE_SESSION_STATUSES or session.runtime_mode != "linux_remote":
            return None
        return self._runtime_for_session(session).viewer_url(session)

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
        runtime = self._runtime_for_session(session)
        if self._is_idle_expired(session):
            runtime.terminate(session)
            session.status = "stopped"
            session.last_error = "Browser session expired due to inactivity."
            session.last_seen_at = utcnow()
            db.session.commit()
            self._refresh_token_file()
            emit_browser_session_update(session.user_id, session.to_dict())
            emit_status(session.user_id, self.status_payload(session.user_id))
            return
        pid_values = [pid for pid in runtime.pid_list(session) if pid]
        if not pid_values or not all(runtime._pid_alive(pid) for pid in pid_values):
            session.status = "failed"
            session.last_error = "One or more runtime processes exited unexpectedly."
            session.last_seen_at = utcnow()
            db.session.commit()
            self._refresh_token_file()
            emit_browser_session_update(session.user_id, session.to_dict())
            emit_status(session.user_id, self.status_payload(session.user_id))

    def _next_value(self, column, start_value: int) -> int:
        max_used = db.session.query(db.func.max(column)).scalar()
        return max(start_value, (max_used or 0) + 1)

    def _refresh_token_file(self) -> None:
        token_file = Path(current_app.config["NOVNC_TOKEN_FILE"])
        token_file.parent.mkdir(parents=True, exist_ok=True)
        active_sessions = BrowserSession.query.filter(
            BrowserSession.status.in_(ACTIVE_SESSION_STATUSES)
        ).all()
        lines = []
        for item in active_sessions:
            mapping = self._runtime_for_session(item).token_mapping(item)
            if mapping:
                lines.append(mapping)
        token_file.write_text("\n".join(lines), encoding="utf-8")

    def _is_idle_expired(self, session: BrowserSession) -> bool:
        active_job = Job.query.filter(
            Job.browser_session_id == session.id,
            Job.status.in_(["starting", "running", "stopping"]),
        ).first()
        if active_job:
            return False
        ttl = timedelta(minutes=current_app.config["BROWSER_IDLE_TTL_MINUTES"])
        return session.last_seen_at < (utcnow() - ttl)

    def _runtime(self):
        runtime_mode = current_app.config["BROWSER_RUNTIME_MODE"]
        if runtime_mode == "linux_remote":
            return LinuxRemoteBrowserRuntime()
        if runtime_mode == "windows_local":
            return WindowsLocalChromeRuntime()
        raise RuntimeError(f"Unsupported browser runtime mode: {runtime_mode}")

    def _runtime_for_session(self, session: BrowserSession):
        if session.runtime_mode == "linux_remote":
            return LinuxRemoteBrowserRuntime()
        if session.runtime_mode == "windows_local":
            return WindowsLocalChromeRuntime()
        raise RuntimeError(f"Unsupported session runtime mode: {session.runtime_mode}")
