from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE_DIR = BASE_DIR / "storage"


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = _require_env("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    BASE_STORAGE_DIR = Path(os.getenv("BASE_STORAGE_DIR", DEFAULT_STORAGE_DIR))
    BROWSER_RUNTIME_MODE = os.getenv("BROWSER_RUNTIME_MODE", "windows_local").strip().lower()
    CHROME_BINARY_PATH = os.getenv("CHROME_BINARY_PATH", "/usr/bin/google-chrome")
    CHROMEDRIVER_BINARY_PATH = os.getenv("CHROMEDRIVER_BINARY_PATH", "")
    WINDOWS_CHROME_BINARY_PATH = os.getenv(
        "WINDOWS_CHROME_BINARY_PATH",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )
    WINDOWS_USER_DATA_ROOT = Path(
        os.getenv(
            "WINDOWS_USER_DATA_ROOT",
            (DEFAULT_STORAGE_DIR / "windows_profiles").as_posix(),
        )
    )

    XVFB_BINARY = os.getenv("XVFB_BINARY", "/usr/bin/Xvfb")
    X11VNC_BINARY = os.getenv("X11VNC_BINARY", "/usr/bin/x11vnc")
    XVFB_START_DISPLAY = int(os.getenv("XVFB_START_DISPLAY", "100"))
    VNC_PORT_START = int(os.getenv("VNC_PORT_START", "5900"))
    DEBUG_PORT_START = int(os.getenv("DEBUG_PORT_START", "9222"))

    NOVNC_BASE_URL = os.getenv("NOVNC_BASE_URL", "http://localhost:6080")
    NOVNC_TOKEN_FILE = Path(
        os.getenv(
            "NOVNC_TOKEN_FILE",
            (DEFAULT_STORAGE_DIR / "novnc" / "tokens").as_posix(),
        )
    )

    SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "480"))
    BROWSER_IDLE_TTL_MINUTES = int(os.getenv("BROWSER_IDLE_TTL_MINUTES", "120"))
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=SESSION_TTL_MINUTES)

    ADMIN_SEED_USERNAME = os.getenv("ADMIN_SEED_USERNAME", "admin")
    ADMIN_SEED_PASSWORD = os.getenv("ADMIN_SEED_PASSWORD", "admin123")
