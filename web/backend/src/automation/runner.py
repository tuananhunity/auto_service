from __future__ import annotations

import random
import time
from threading import Event

from flask import current_app

from ..models import BrowserSession, CommentSet, GroupSet, Job
from .browser import attach_to_debug_port


class RemoteBrowserAutomationRunner:
    """
    Generic Selenium runner attached to a live server-side Chrome session.

    This worker stays provider-agnostic and only demonstrates the job lifecycle
    against user-supplied target URLs while the browser remains under dashboard control.
    """

    def __init__(
        self,
        job: Job,
        browser_session: BrowserSession,
        group_set: GroupSet,
        comment_set: CommentSet,
        stop_event: Event,
        log_callback,
    ) -> None:
        self.job = job
        self.browser_session = browser_session
        self.group_set = group_set
        self.comment_set = comment_set
        self.stop_event = stop_event
        self.log_callback = log_callback
        self.driver = None

    def _log(self, message: str, level: str = "info") -> None:
        self.log_callback(level, message)

    def _check_stop(self) -> None:
        if self.stop_event.is_set():
            raise InterruptedError("Job stopped by user")

    def run(self) -> None:
        self.driver = attach_to_debug_port(
            debug_port=self.browser_session.debug_port,
            chrome_binary_path=current_app.config["CHROME_BINARY_PATH"],
            driver_binary_path=current_app.config["CHROMEDRIVER_BINARY_PATH"] or None,
        )
        self._log("Attached Selenium to the live browser session.")

        targets = self.group_set.items or []
        comments = self.comment_set.items or []
        delay_seconds = int((self.job.config or {}).get("delay", 5))

        for index, target in enumerate(targets, start=1):
            self._check_stop()
            self._log(f"Opening target {index}/{len(targets)}: {target}")
            self.driver.get(target)
            time.sleep(max(1, delay_seconds))

            if comments:
                preview = random.choice(comments)
                self._log(f"Loaded page. Comment candidate available: {preview[:120]}")
            else:
                self._log("Loaded page. No comment candidates configured.", "warning")

        self._log("Job finished its queued browser actions.", "success")

    def cleanup(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
