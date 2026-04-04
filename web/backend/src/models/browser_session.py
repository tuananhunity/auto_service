from __future__ import annotations

from ..extensions import db
from .base import utcnow


class BrowserSession(db.Model):
    __tablename__ = "browser_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="idle")
    runtime_mode = db.Column(db.String(30), nullable=False, default="windows_local")
    viewer_type = db.Column(db.String(20), nullable=False, default="none")
    viewer_url = db.Column(db.String(500))
    display_number = db.Column(db.Integer)
    vnc_port = db.Column(db.Integer)
    debug_port = db.Column(db.Integer, nullable=False)
    novnc_token = db.Column(db.String(120), unique=True)
    profile_path = db.Column(db.String(500), nullable=False)
    chrome_pid = db.Column(db.Integer)
    xvfb_pid = db.Column(db.Integer)
    x11vnc_pid = db.Column(db.Integer)
    last_error = db.Column(db.Text)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    user = db.relationship("User", back_populates="browser_sessions")
    jobs = db.relationship("Job", back_populates="browser_session")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "runtime_mode": self.runtime_mode,
            "viewer_type": self.viewer_type,
            "viewer_url": self.viewer_url,
            "display_number": self.display_number,
            "vnc_port": self.vnc_port,
            "debug_port": self.debug_port,
            "novnc_token": self.novnc_token,
            "profile_path": self.profile_path,
            "last_error": self.last_error,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
