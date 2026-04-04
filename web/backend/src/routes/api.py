from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import CommentSet, GroupSet, Job
from ..services.auth import get_current_user, login_required
from ..services.browser_sessions import BrowserSessionManager
from ..services.jobs import job_manager
from ..utils.validators import normalize_line_items

api_bp = Blueprint("api", __name__)
browser_session_manager = BrowserSessionManager()


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _upsert_data_set(model, user_id: int, name: str, items: list[str]):
    record_id = request.json.get("id")
    if record_id:
        record = model.query.filter_by(id=record_id, user_id=user_id).first_or_404()
        record.name = name
        record.items = items
    else:
        record = model(user_id=user_id, name=name, items=items)
        db.session.add(record)
    db.session.commit()
    return record


@api_bp.route("/me", methods=["GET"])
@login_required
def api_me():
    user = get_current_user()
    browser_session = browser_session_manager.latest_for_user(user)
    active_job = (
        Job.query.filter(
            Job.user_id == user.id,
            Job.status.in_(["starting", "running", "stopping"]),
        )
        .order_by(Job.created_at.desc())
        .first()
    )
    return jsonify(
        {
            "user": user.to_dict(),
            "browser_session": browser_session.to_dict() if browser_session else None,
            "active_job": active_job.to_dict() if active_job else None,
        }
    )


@api_bp.route("/browser-sessions/open", methods=["POST"])
@login_required
def api_open_browser_session():
    user = get_current_user()
    try:
        session = browser_session_manager.open_for_user(user)
    except Exception as exc:
        return _json_error(str(exc))
    return jsonify({"browser_session": session.to_dict()})


@api_bp.route("/browser-sessions/<int:session_id>", methods=["GET"])
@login_required
def api_get_browser_session(session_id: int):
    user = get_current_user()
    session = browser_session_manager.get_for_user(user, session_id)
    return jsonify(
        {
            "browser_session": session.to_dict(),
            "viewer_url": session.viewer_url,
        }
    )


@api_bp.route("/browser-sessions/<int:session_id>/close", methods=["POST"])
@login_required
def api_close_browser_session(session_id: int):
    user = get_current_user()
    try:
        session = browser_session_manager.close_for_user(user, session_id)
    except Exception as exc:
        return _json_error(str(exc))
    return jsonify({"browser_session": session.to_dict()})


@api_bp.route("/group-sets", methods=["GET", "POST"])
@login_required
def api_group_sets():
    user = get_current_user()
    if request.method == "GET":
        records = GroupSet.query.filter_by(user_id=user.id).order_by(GroupSet.updated_at.desc()).all()
        return jsonify({"items": [record.to_dict() for record in records]})

    payload = request.json or {}
    name = (payload.get("name") or "Default Target Set").strip()
    items = normalize_line_items(payload.get("items"))
    record = _upsert_data_set(GroupSet, user.id, name, items)
    return jsonify({"item": record.to_dict()})


@api_bp.route("/comment-sets", methods=["GET", "POST"])
@login_required
def api_comment_sets():
    user = get_current_user()
    if request.method == "GET":
        records = CommentSet.query.filter_by(user_id=user.id).order_by(CommentSet.updated_at.desc()).all()
        return jsonify({"items": [record.to_dict() for record in records]})

    payload = request.json or {}
    name = (payload.get("name") or "Default Comment Set").strip()
    items = normalize_line_items(payload.get("items"))
    record = _upsert_data_set(CommentSet, user.id, name, items)
    return jsonify({"item": record.to_dict()})


@api_bp.route("/jobs/start", methods=["POST"])
@login_required
def api_start_job():
    user = get_current_user()
    payload = request.json or {}
    try:
        job = job_manager.start_for_user(
            user=user,
            browser_session_id=int(payload["browser_session_id"]),
            group_set_id=int(payload["group_set_id"]),
            comment_set_id=int(payload["comment_set_id"]),
            config={
                "delay": int(payload.get("delay", 5)),
                "max_posts": int(payload.get("max_posts", 5)),
            },
        )
    except KeyError as exc:
        return _json_error(f"Missing field: {exc}")
    except Exception as exc:
        return _json_error(str(exc))
    return jsonify({"job": job.to_dict()})


@api_bp.route("/jobs/<int:job_id>/stop", methods=["POST"])
@login_required
def api_stop_job(job_id: int):
    user = get_current_user()
    try:
        job = job_manager.stop_for_user(user, job_id)
    except Exception as exc:
        return _json_error(str(exc))
    return jsonify({"job": job.to_dict()})


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
@login_required
def api_get_job(job_id: int):
    user = get_current_user()
    job = Job.query.filter_by(id=job_id, user_id=user.id).first_or_404()
    return jsonify({"job": job.to_dict()})


@api_bp.route("/jobs/<int:job_id>/logs", methods=["GET"])
@login_required
def api_get_job_logs(job_id: int):
    user = get_current_user()
    job = Job.query.filter_by(id=job_id, user_id=user.id).first_or_404()
    return jsonify({"items": [log.to_dict() for log in job.logs[-200:]]})
