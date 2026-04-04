from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import User
from ..services.auth import get_current_user, login_user, logout_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html")

        login_user(user)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
