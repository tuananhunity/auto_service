from __future__ import annotations

from ..extensions import db
from ..models import BrowserSession, Job, JobLog
from ..models.base import utcnow
from .browser_runtime import LinuxRemoteBrowserRuntime, WindowsLocalChromeRuntime


ACTIVE_JOB_STATUSES = {"starting", "running", "stopping"}
ACTIVE_SESSION_STATUSES = {"starting", "ready", "busy"}


def reconcile_runtime_state() -> None:
    jobs = Job.query.filter(Job.status.in_(ACTIVE_JOB_STATUSES)).all()
    orphaned_session_ids = set()

    for job in jobs:
        job.status = "failed"
        job.last_error = "Application restarted before the in-memory worker could finish the job."
        job.finished_at = utcnow()
        orphaned_session_ids.add(job.browser_session_id)
        db.session.add(
            JobLog(
                job_id=job.id,
                level="error",
                message="Job marked failed during startup recovery after an application restart.",
            )
        )

    sessions = BrowserSession.query.filter(BrowserSession.status.in_(ACTIVE_SESSION_STATUSES)).all()
    for session in sessions:
        runtime = _runtime_for_session(session)
        alive_pids = [pid for pid in runtime.pid_list(session) if pid]
        is_alive = bool(alive_pids) and all(runtime._pid_alive(pid) for pid in alive_pids)

        if session.id in orphaned_session_ids:
            session.status = "ready" if is_alive else "failed"
            session.last_error = None if is_alive else "Browser runtime was not available after startup recovery."
            continue

        if session.status == "starting":
            session.status = "ready" if is_alive else "failed"
            session.last_error = None if is_alive else "Browser session did not survive application restart."
            continue

        if session.status == "busy":
            session.status = "ready" if is_alive else "failed"
            session.last_error = None if is_alive else "Browser session became unavailable during application restart."
            continue

        if session.status == "ready" and not is_alive:
            session.status = "failed"
            session.last_error = "Browser runtime was not available after application restart."

    db.session.commit()


def _runtime_for_session(session: BrowserSession):
    if session.runtime_mode == "linux_remote":
        return LinuxRemoteBrowserRuntime()
    if session.runtime_mode == "windows_local":
        return WindowsLocalChromeRuntime()
    raise RuntimeError(f"Unsupported session runtime mode: {session.runtime_mode}")
