from __future__ import annotations

from pathlib import Path

from flask import current_app


def ensure_storage_tree() -> None:
    base_dir = Path(current_app.config["BASE_STORAGE_DIR"])
    for path in [
        base_dir,
        base_dir / "browser_profiles",
        base_dir / "novnc",
        base_dir / "runtime",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def browser_profile_path(user_id: int) -> Path:
    path = Path(current_app.config["BASE_STORAGE_DIR"]) / "browser_profiles" / str(user_id) / "default"
    path.mkdir(parents=True, exist_ok=True)
    return path
