# Web Dashboard

This folder contains an independent Flask web application for:

- internal user authentication
- server-side browser session lifecycle
- PostgreSQL-backed data sets and job records
- Windows local Chrome dev mode and Linux noVNC remote mode
- Socket.IO status and log streaming

## Quick start

1. Create a virtual environment and install `web/backend/requirements.txt`.
2. Create a local PostgreSQL database, for example `remote_browser_dev`.
3. Configure `DATABASE_URL`, `SECRET_KEY`, `BASE_STORAGE_DIR`, and `BROWSER_RUNTIME_MODE`.
4. For Windows dev mode, ensure Chrome is installed and `WINDOWS_CHROME_BINARY_PATH` is correct.
5. Run `python web/backend/scripts/seed_admin.py`.
6. Start the app with `python web/backend/app.py`.

## Windows dev mode

Use:

- `BROWSER_RUNTIME_MODE=windows_local`
- local PostgreSQL
- local Chrome opened directly on the Windows desktop

In this mode, the dashboard controls the job/session lifecycle, but the browser is not embedded in the page.

You can connect DBeaver to the same local PostgreSQL instance to inspect:

- `users`
- `browser_sessions`
- `jobs`
- `job_logs`
- `group_sets`
- `comment_sets`

## Linux remote mode

Use:

- `BROWSER_RUNTIME_MODE=linux_remote`
- `google-chrome`
- `Xvfb`
- `x11vnc`
- `websockify` / noVNC

Then start the noVNC proxy with `sh web/docker/run_websockify.sh`, or use `docker compose -f web/docker/docker-compose.yml up --build`.

## Notes

- `web/` is isolated from `app/` and does not import from it.
- `DATABASE_URL` is required; SQLite fallback is no longer used.
- The job pipeline attaches Selenium to a live browser session through Chrome remote debugging.
