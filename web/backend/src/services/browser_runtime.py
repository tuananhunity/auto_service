from __future__ import annotations

import os
import platform
import secrets
import signal
import subprocess
import time
from pathlib import Path

from flask import current_app

from ..models import BrowserSession
from ..utils.paths import browser_profile_path, windows_browser_profile_path


class BaseBrowserRuntime:
    runtime_mode = "base"
    viewer_type = "none"

    def prepare_session(self, session: BrowserSession) -> None:
        raise NotImplementedError

    def launch(self, session: BrowserSession) -> None:
        raise NotImplementedError

    def terminate(self, session: BrowserSession) -> None:
        for pid in [session.chrome_pid, session.x11vnc_pid, session.xvfb_pid]:
            self._terminate_pid(pid)
        session.chrome_pid = None
        session.x11vnc_pid = None
        session.xvfb_pid = None

    def viewer_url(self, session: BrowserSession) -> str | None:
        return session.viewer_url

    def token_mapping(self, session: BrowserSession) -> str | None:
        return None

    def pid_list(self, session: BrowserSession) -> list[int | None]:
        return [session.chrome_pid]

    def _pid_alive(self, pid: int | None) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _terminate_pid(self, pid: int | None) -> None:
        if not pid or not self._pid_alive(pid):
            return
        if platform.system().lower() == "windows":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
        try:
            os.killpg(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


class LinuxRemoteBrowserRuntime(BaseBrowserRuntime):
    runtime_mode = "linux_remote"
    viewer_type = "novnc"

    def prepare_session(self, session: BrowserSession) -> None:
        session.runtime_mode = self.runtime_mode
        session.viewer_type = self.viewer_type
        session.novnc_token = session.novnc_token or secrets.token_urlsafe(18)
        session.profile_path = str(browser_profile_path(session.user_id))
        session.viewer_url = self.viewer_url(session)

    def launch(self, session: BrowserSession) -> None:
        if platform.system().lower() != "linux":
            raise RuntimeError("Linux remote browser runtime requires a Linux host.")

        xvfb_process = subprocess.Popen(
            [
                current_app.config["XVFB_BINARY"],
                f":{session.display_number}",
                "-screen",
                "0",
                "1440x900x24",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1)

        x11vnc_process = subprocess.Popen(
            [
                current_app.config["X11VNC_BINARY"],
                "-display",
                f":{session.display_number}",
                "-rfbport",
                str(session.vnc_port),
                "-forever",
                "-shared",
                "-localhost",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        env = os.environ.copy()
        env["DISPLAY"] = f":{session.display_number}"

        chrome_process = subprocess.Popen(
            [
                current_app.config["CHROME_BINARY_PATH"],
                f"--user-data-dir={session.profile_path}",
                f"--remote-debugging-port={session.debug_port}",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--window-size=1440,900",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )

        session.xvfb_pid = xvfb_process.pid
        session.x11vnc_pid = x11vnc_process.pid
        session.chrome_pid = chrome_process.pid
        session.viewer_url = self.viewer_url(session)

        if not all(self._pid_alive(pid) for pid in self.pid_list(session)):
            raise RuntimeError("Failed to launch the Linux remote browser runtime.")

    def viewer_url(self, session: BrowserSession) -> str | None:
        if not session.novnc_token:
            return None
        base = current_app.config["NOVNC_BASE_URL"].rstrip("/")
        return f"{base}/vnc.html?autoconnect=true&resize=remote&path=websockify?token={session.novnc_token}"

    def token_mapping(self, session: BrowserSession) -> str | None:
        if not session.novnc_token or not session.vnc_port:
            return None
        return f"{session.novnc_token}: 127.0.0.1:{session.vnc_port}"

    def pid_list(self, session: BrowserSession) -> list[int | None]:
        return [session.chrome_pid, session.x11vnc_pid, session.xvfb_pid]


class WindowsLocalChromeRuntime(BaseBrowserRuntime):
    runtime_mode = "windows_local"
    viewer_type = "external"

    def prepare_session(self, session: BrowserSession) -> None:
        session.runtime_mode = self.runtime_mode
        session.viewer_type = self.viewer_type
        session.display_number = None
        session.vnc_port = None
        session.novnc_token = None
        session.xvfb_pid = None
        session.x11vnc_pid = None
        session.profile_path = str(windows_browser_profile_path(session.user_id))
        session.viewer_url = None

    def launch(self, session: BrowserSession) -> None:
        if platform.system().lower() != "windows":
            raise RuntimeError("Windows local runtime requires a Windows host.")

        chrome_binary = current_app.config["WINDOWS_CHROME_BINARY_PATH"]
        chrome_process = subprocess.Popen(
            [
                chrome_binary,
                f"--user-data-dir={session.profile_path}",
                f"--remote-debugging-port={session.debug_port}",
                "--new-window",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

        session.chrome_pid = chrome_process.pid
        session.viewer_url = None

        if not self._pid_alive(session.chrome_pid):
            raise RuntimeError("Failed to launch local Chrome for Windows dev mode.")
