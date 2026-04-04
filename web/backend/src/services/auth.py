from __future__ import annotations

from functools import wraps

from flask import g, redirect, request, session, url_for

from ..models import User


def get_current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    if getattr(g, "_current_user", None) is None:
        g._current_user = User.query.get(user_id)
    return g._current_user


def login_user(user: User) -> None:
    session.permanent = True
    session["user_id"] = user.id


def logout_user() -> None:
    session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not get_current_user():
            if request.path.startswith("/api/"):
                return {"error": "Unauthorized"}, 401
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped
