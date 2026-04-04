from __future__ import annotations

from flask import session
from flask_socketio import join_room

from ..models import Job
from ..services.auth import get_current_user
from ..services.browser_sessions import BrowserSessionManager
from ..services.event_bus import emit_browser_session_update, emit_job_update, emit_status, user_room


def register_socket_handlers(socketio):
    browser_session_manager = BrowserSessionManager()

    @socketio.on("connect")
    def handle_connect():
        if not session.get("user_id"):
            return False

        user = get_current_user()
        if not user:
            return False

        join_room(user_room(user.id))
        browser_session = browser_session_manager.latest_for_user(user)
        active_job = (
            Job.query.filter(
                Job.user_id == user.id,
                Job.status.in_(["starting", "running", "stopping"]),
            )
            .order_by(Job.created_at.desc())
            .first()
        )
        emit_status(
            user.id,
            {
                "browser_session": browser_session.to_dict() if browser_session else None,
                "active_job": active_job.to_dict() if active_job else None,
            },
        )
        if browser_session:
            emit_browser_session_update(user.id, browser_session.to_dict())
        if active_job:
            emit_job_update(user.id, active_job.to_dict())
