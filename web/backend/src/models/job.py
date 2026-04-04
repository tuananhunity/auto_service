from __future__ import annotations

from ..extensions import db
from .base import utcnow


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    browser_session_id = db.Column(
        db.Integer,
        db.ForeignKey("browser_sessions.id"),
        nullable=False,
        index=True,
    )
    group_set_id = db.Column(db.Integer, db.ForeignKey("group_sets.id"), nullable=False)
    comment_set_id = db.Column(db.Integer, db.ForeignKey("comment_sets.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="idle")
    config = db.Column(db.JSON, nullable=False, default=dict)
    last_error = db.Column(db.Text)
    started_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    user = db.relationship("User", back_populates="jobs")
    browser_session = db.relationship("BrowserSession", back_populates="jobs")
    logs = db.relationship(
        "JobLog",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobLog.created_at.asc()",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "browser_session_id": self.browser_session_id,
            "group_set_id": self.group_set_id,
            "comment_set_id": self.comment_set_id,
            "status": self.status,
            "config": self.config or {},
            "last_error": self.last_error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
