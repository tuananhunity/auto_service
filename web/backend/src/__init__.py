from flask import Flask

from .config import Config
from .extensions import db, socketio
from .routes.api import api_bp
from .routes.auth import auth_bp
from .routes.dashboard import dashboard_bp
from .routes.socket_events import register_socket_handlers


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_object)

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config["CORS_ALLOWED_ORIGINS"])

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    register_socket_handlers(socketio)

    with app.app_context():
        from . import models  # noqa: F401

        db.create_all()

    return app
