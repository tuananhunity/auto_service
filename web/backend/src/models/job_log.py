from __future__ import annotations

from ..extensions import db
from .base import utcnow


class JobLog(db.Model):
    __tablename__ = "job_logs"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, default="info")
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    job = db.relationship("Job", back_populates="logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "level": self.level,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }
