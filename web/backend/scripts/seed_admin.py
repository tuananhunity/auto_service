from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src import create_app
from src.config import Config
from src.extensions import db
from src.models import User


def main() -> None:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=Config.ADMIN_SEED_USERNAME).first()
        if user:
            print(f"Admin user '{user.username}' already exists.")
            return

        user = User(username=Config.ADMIN_SEED_USERNAME, role="admin")
        user.set_password(Config.ADMIN_SEED_PASSWORD)
        db.session.add(user)
        db.session.commit()
        print(f"Created admin user '{user.username}'.")


if __name__ == "__main__":
    main()
