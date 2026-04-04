from __future__ import annotations

import threading

from flask import current_app

from ..automation.runner import RemoteBrowserAutomationRunner
from ..extensions import db
from ..models import BrowserSession, CommentSet, GroupSet, Job, JobLog, User
from ..models.base import utcnow
from .browser_sessions import BrowserSessionManager
from .event_bus import emit_job_log, emit_job_update, emit_status


ACTIVE_JOB_STATUSES = {"starting", "running", "stopping"}


class JobManager:
    def __init__(self) -> None:
        self._threads: dict[int, threading.Thread] = {}
        self._stop_events: dict[int, threading.Event] = {}
        self._lock = threading.Lock()
        self.browser_session_manager = BrowserSessionManager()

    def start_for_user(
        self,
        user: User,
        browser_session_id: int,
        group_set_id: int,
        comment_set_id: int,
        config: dict,
    ) -> Job:
        active_job = Job.query.filter(
            Job.user_id == user.id,
            Job.status.in_(ACTIVE_JOB_STATUSES),
        ).first()
        if active_job:
            raise ValueError("User already has an active job.")

        session = BrowserSession.query.filter_by(id=browser_session_id, user_id=user.id).first_or_404()
        if session.status != "ready":
            raise ValueError("Browser session must be ready before starting a job.")

        group_set = GroupSet.query.filter_by(id=group_set_id, user_id=user.id).first_or_404()
        comment_set = CommentSet.query.filter_by(id=comment_set_id, user_id=user.id).first_or_404()

        job = Job(
            user_id=user.id,
            browser_session_id=session.id,
            group_set_id=group_set.id,
            comment_set_id=comment_set.id,
            status="starting",
            config=config,
            started_at=utcnow(),
        )
        db.session.add(job)
        db.session.commit()

        self._write_log(job, "info", "Job queued and waiting for worker startup.")
        self._emit_job_status(job)

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._run_job,
            args=(current_app._get_current_object(), job.id, stop_event),
            daemon=True,
        )

        with self._lock:
            self._stop_events[job.id] = stop_event
            self._threads[job.id] = thread

        thread.start()
        return job

    def stop_for_user(self, user: User, job_id: int) -> Job:
        job = Job.query.filter_by(id=job_id, user_id=user.id).first_or_404()
        if job.status not in ACTIVE_JOB_STATUSES:
            raise ValueError("Job is not running.")

        job.status = "stopping"
        db.session.commit()
        self._write_log(job, "warning", "Stop requested by user.")

        with self._lock:
            stop_event = self._stop_events.get(job.id)
            if stop_event:
                stop_event.set()

        self._emit_job_status(job)
        return job

    def _run_job(self, app, job_id: int, stop_event: threading.Event) -> None:
        with app.app_context():
            job = Job.query.get(job_id)
            if not job:
                return

            runner = RemoteBrowserAutomationRunner(
                job=job,
                browser_session=BrowserSession.query.get(job.browser_session_id),
                group_set=GroupSet.query.get(job.group_set_id),
                comment_set=CommentSet.query.get(job.comment_set_id),
                stop_event=stop_event,
                log_callback=lambda level, message: self._write_log(job, level, message),
            )

            try:
                job.status = "running"
                browser_session = BrowserSession.query.get(job.browser_session_id)
                if browser_session:
                    browser_session.status = "busy"
                db.session.commit()
                self._emit_job_status(job)
                runner.run()
                job.status = "completed"
                job.finished_at = utcnow()
                browser_session = BrowserSession.query.get(job.browser_session_id)
                if browser_session and browser_session.status == "busy":
                    browser_session.status = "ready"
                db.session.commit()
                self._emit_job_status(job)
            except InterruptedError:
                job.status = "stopped"
                job.finished_at = utcnow()
                browser_session = BrowserSession.query.get(job.browser_session_id)
                if browser_session and browser_session.status == "busy":
                    browser_session.status = "ready"
                db.session.commit()
                self._write_log(job, "warning", "Job stopped before completion.")
                self._emit_job_status(job)
            except Exception as exc:
                job.status = "failed"
                job.last_error = str(exc)
                job.finished_at = utcnow()
                browser_session = BrowserSession.query.get(job.browser_session_id)
                if browser_session and browser_session.status == "busy":
                    browser_session.status = "ready"
                db.session.commit()
                self._write_log(job, "error", f"Job failed: {exc}")
                self._emit_job_status(job)
            finally:
                runner.cleanup()
                with self._lock:
                    self._threads.pop(job.id, None)
                    self._stop_events.pop(job.id, None)

    def _write_log(self, job: Job, level: str, message: str) -> None:
        log = JobLog(job_id=job.id, level=level, message=message)
        db.session.add(log)
        db.session.commit()
        emit_job_log(job.user_id, log.to_dict())

    def _emit_job_status(self, job: Job) -> None:
        active_job = (
            Job.query.filter(
                Job.user_id == job.user_id,
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
            .order_by(Job.created_at.desc())
            .first()
        )
        browser_session = self.browser_session_manager.latest_for_user(job.user)
        emit_job_update(job.user_id, job.to_dict())
        emit_status(
            job.user_id,
            {
                "browser_session": browser_session.to_dict() if browser_session else None,
                "active_job": active_job.to_dict() if active_job else None,
            },
        )


job_manager = JobManager()
