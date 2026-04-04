from __future__ import annotations

from ..extensions import socketio


def user_room(user_id: int) -> str:
    return f"user:{user_id}"


def emit_status(user_id: int, payload: dict) -> None:
    socketio.emit("status_update", payload, to=user_room(user_id))


def emit_browser_session_update(user_id: int, payload: dict) -> None:
    socketio.emit("browser_session_update", payload, to=user_room(user_id))


def emit_job_update(user_id: int, payload: dict) -> None:
    socketio.emit("job_update", payload, to=user_room(user_id))


def emit_job_log(user_id: int, payload: dict) -> None:
    socketio.emit("job_log", payload, to=user_room(user_id))
