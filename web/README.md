# Web Dashboard

This folder contains an independent Flask web application for:

- internal user authentication
- server-side browser session lifecycle
- PostgreSQL-backed data sets and job records
- noVNC embedding for remote browser access
- Socket.IO status and log streaming

## Quick start

1. Create a virtual environment and install `web/backend/requirements.txt`.
2. Configure `DATABASE_URL`, `SECRET_KEY`, `BASE_STORAGE_DIR`, and Linux browser runtime binaries.
3. Run `python web/backend/scripts/seed_admin.py`.
4. Start the app with `python web/backend/app.py`.
5. Start the noVNC proxy with `sh web/docker/run_websockify.sh`, or use `docker compose -f web/docker/docker-compose.yml up --build`.

## Linux runtime requirements

The remote browser runtime expects these binaries on the host:

- `google-chrome`
- `Xvfb`
- `x11vnc`
- `websockify` / noVNC configured against the generated token file

## Notes

- `web/` is isolated from `app/` and does not import from it.
- Browser runtime is implemented for Linux hosts only.
- The job pipeline attaches Selenium to a live remote browser session through Chrome remote debugging.
