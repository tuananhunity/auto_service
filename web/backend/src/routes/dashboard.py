from __future__ import annotations

from flask import Blueprint, render_template

from ..services.auth import get_current_user, login_required
from ..services.browser_sessions import BrowserSessionManager

dashboard_bp = Blueprint("dashboard", __name__)
browser_session_manager = BrowserSessionManager()


@dashboard_bp.route("/")
def root():
    return render_template("dashboard/landing.html")


@dashboard_bp.route("/dashboard")
@login_required
def index():
    user = get_current_user()
    browser_session = browser_session_manager.latest_for_user(user)
    return render_template(
        "dashboard/index.html",
        current_user=user,
        browser_session=browser_session,
        viewer_url=browser_session.viewer_url if browser_session else None,
    )


@dashboard_bp.route("/remote-browser/<int:session_id>")
@login_required
def remote_browser(session_id: int):
    user = get_current_user()
    browser_session = browser_session_manager.get_for_user(user, session_id)
    return render_template(
        "dashboard/remote_browser.html",
        current_user=user,
        browser_session=browser_session,
        viewer_url=browser_session.viewer_url,
    )
