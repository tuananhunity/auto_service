from __future__ import annotations

from ..extensions import db
from .base import utcnow


class GroupSet(db.Model):
    __tablename__ = "group_sets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    items = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    user = db.relationship("User", back_populates="group_sets")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "items": self.items or [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
