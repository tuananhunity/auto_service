from __future__ import annotations

import math
import random
import time
from threading import Event

from flask import current_app
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from ..models import BrowserSession, CommentSet, GroupSet, Job
from .browser import attach_to_debug_port


class RemoteBrowserAutomationRunner:
    """
    Selenium automation runner attached to a live browser session.
    """

    COMMENT_BOX_XPATH = (
        "//div["
        "("
        "contains(@aria-label, 'Write a comment') "
        "or contains(@aria-label, 'Viết bình luận') "
        "or contains(@aria-label, 'Bình luận dưới tên') "
        "or contains(@aria-label, 'Bình luận công khai')"
        ") and @contenteditable='true'"
        "]"
    )
    COMMENT_TRIGGER_XPATH = (
        ".//*[(@role='button' or @tabindex='0' or @role='link') and ("
        "contains(translate(@aria-label, 'BCMNL', 'bcmnl'), 'comment') "
        "or contains(translate(@aria-label, 'BCMNL', 'bcmnl'), 'bình luận') "
        "or contains(translate(., 'BCMNL', 'bcmnl'), 'comment') "
        "or contains(translate(., 'BCMNL', 'bcmnl'), 'bình luận'))]"
    )
    BAD_COMMENT_BUTTON_WORDS = (
        "nhãn dán",
        "gif",
        "avatar",
        "sticker",
        "file đính kèm",
        "attachment",
        "mới",
        "xem thêm",
    )
    DEFAULT_COMMENT = "Tuyet voi!"

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

    def _random_pause(self, min_seconds: float = 1, max_seconds: float = 5) -> None:
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _human_mouse_jiggle(self, element, moves: int = 2) -> None:
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            for _ in range(moves):
                actions.move_by_offset(random.randint(-15, 15), random.randint(-15, 15)).perform()
                self._random_pause(0.2, 0.6)
            actions.move_to_element(element).perform()
            self._random_pause(0.2, 0.6)
        except Exception:
            pass

    def _human_type(self, element, text: str) -> None:
        words = text.split()
        for word_index, word in enumerate(words):
            if random.random() < 0.05:
                fake_word = random.choice(["aaa", "zzz", "hmm"])
                for char in fake_word:
                    element.send_keys(char)
                    time.sleep(random.uniform(0.08, 0.25))
                for _ in fake_word:
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.06, 0.18))

            for char in word:
                if random.random() < 0.05:
                    typo = random.choice("abcdefghijklmnopqrstuvwxyz")
                    element.send_keys(typo)
                    time.sleep(random.uniform(0.08, 0.25))
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.06, 0.18))
                element.send_keys(char)
                time.sleep(random.uniform(0.08, 0.25))

            if word_index < len(words) - 1:
                element.send_keys(" ")
                time.sleep(random.uniform(0.08, 0.2))

        self._random_pause(0.5, 1.2)

    def _mark_article_processed(self, article) -> None:
        try:
            self.driver.execute_script(
                "arguments[0].setAttribute('data-bot-commented', 'true');",
                article,
            )
        except Exception:
            pass

    def _is_text_input(self, element) -> bool:
        if not element:
            return False
        try:
            if element.get_attribute("contenteditable") == "true":
                return True
            return (element.tag_name or "").lower() in {"input", "textarea"}
        except Exception:
            return False

    def _find_visible_comment_box(self, scope, xpath: str):
        try:
            boxes = scope.find_elements(By.XPATH, xpath)
        except Exception:
            return None

        for box in boxes:
            try:
                if box.is_displayed():
                    return box
            except StaleElementReferenceException:
                continue
        return None

    def _candidate_metadata(self, button) -> tuple[str, str, str]:
        text = ((button.text or "").strip()).lower()
        aria = ((button.get_attribute("aria-label") or "").strip()).lower()
        combined = f"{text} {aria}".strip()
        return text, aria, combined

    def _has_nested_comment_target(self, button) -> bool:
        try:
            descendants = button.find_elements(By.XPATH, ".//*")
        except Exception:
            return False

        for descendant in descendants:
            try:
                if descendant == button or not descendant.is_displayed():
                    continue
                text, aria, combined = self._candidate_metadata(descendant)
                if ("bình luận" in combined or "comment" in combined) and len(text) < 50:
                    return True
            except Exception:
                continue
        return False

    def _comment_button_score(self, button) -> float | None:
        try:
            if not button.is_displayed():
                return None
            text, aria, combined = self._candidate_metadata(button)
            if ("bình luận" not in combined and "comment" not in combined):
                return None
            if any(bad_word in combined for bad_word in self.BAD_COMMENT_BUTTON_WORDS):
                return None
            if len(text) >= 50:
                return None
            if self._has_nested_comment_target(button):
                return None

            rect = button.rect or {}
            width = float(rect.get("width") or 0)
            height = float(rect.get("height") or 0)
            area = width * height
            if width > 260 or height > 120 or area > 20000:
                return None

            score = 0.0
            if text in {"comment", "bình luận"}:
                score += 120
            if aria in {"comment", "bình luận"}:
                score += 120
            if "comment" in text or "bình luận" in text:
                score += 60
            if "comment" in aria or "bình luận" in aria:
                score += 60
            if button.get_attribute("role") == "button":
                score += 20
            if button.tag_name.lower() in {"div", "span"}:
                score += 5

            score -= math.sqrt(max(area, 1))
            return score
        except Exception:
            return None

    def _find_comment_button(self, article):
        try:
            buttons = article.find_elements(By.XPATH, self.COMMENT_TRIGGER_XPATH)
        except Exception:
            return None

        best_button = None
        best_score = None
        for button in buttons:
            try:
                score = self._comment_button_score(button)
                if score is None:
                    continue
                if best_score is None or score > best_score:
                    best_button = button
                    best_score = score
            except StaleElementReferenceException:
                continue
            except Exception:
                continue
        return best_button

    def _resolve_comment_target(self, article):
        inline_box = self._find_visible_comment_box(article, "." + self.COMMENT_BOX_XPATH)
        if inline_box:
            return inline_box

        trigger = self._find_comment_button(article)
        if not trigger:
            self._mark_article_processed(article)
            return None

        trigger_text, trigger_aria, _ = self._candidate_metadata(trigger)
        self._log(
            "Found a candidate post without an open box. "
            f"Expanding the comment composer using text='{trigger_text}' aria='{trigger_aria}'."
        )
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trigger)
        self._random_pause(1, 2)
        try:
            self._human_mouse_jiggle(trigger, moves=2)
            trigger.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", trigger)

        self._random_pause(1, 2)

        active_element = self.driver.switch_to.active_element
        if self._is_text_input(active_element):
            return active_element

        global_box = self._find_visible_comment_box(self.driver, self.COMMENT_BOX_XPATH)
        if global_box:
            return global_box

        self._mark_article_processed(article)
        return None

    def _find_next_comment_target(self):
        articles = self.driver.find_elements(By.XPATH, "//div[@role='article']")
        for article in articles:
            self._check_stop()
            try:
                if article.get_attribute("data-bot-commented") == "true":
                    continue
                if not article.is_displayed():
                    continue
            except StaleElementReferenceException:
                continue

            target = self._resolve_comment_target(article)
            if target:
                return article, target

        return None, None

    def _generate_comment(self, comments: list[str]) -> str:
        if comments:
            return random.choice(comments)
        return self.DEFAULT_COMMENT

    def _dismiss_comment_overlay(self) -> None:
        try:
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.5)
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        except Exception:
            pass

    def run(self) -> None:
        chrome_binary = (
            current_app.config["WINDOWS_CHROME_BINARY_PATH"]
            if self.browser_session.runtime_mode == "windows_local"
            else current_app.config["CHROME_BINARY_PATH"]
        )
        self.driver = attach_to_debug_port(
            debug_port=self.browser_session.debug_port,
            chrome_binary_path=chrome_binary,
            driver_binary_path=current_app.config["CHROMEDRIVER_BINARY_PATH"] or None,
        )
        self._log("Attached Selenium to the live browser session.")

        targets = [(target or "").strip() for target in (self.group_set.items or []) if (target or "").strip()]
        comments = [(comment or "").strip() for comment in (self.comment_set.items or []) if (comment or "").strip()]
        delay_seconds = max(1, int((self.job.config or {}).get("delay", 5)))
        max_posts_per_target = max(1, int((self.job.config or {}).get("max_posts", 5)))

        if not targets:
            self._log("No target URLs configured for this job.", "warning")
            return
        if not comments:
            self._log("No comment candidates configured. Falling back to the default comment.", "warning")

        for index, target in enumerate(targets, start=1):
            self._check_stop()
            self._log(f"Opening target {index}/{len(targets)}: {target}")
            self.driver.get(target)
            self._random_pause(5, 8)

            comment_count = 0
            scroll_fails = 0
            max_scroll_attempts = 15

            while comment_count < max_posts_per_target and scroll_fails < max_scroll_attempts:
                self._check_stop()
                self._log(f"Scanning posts ({comment_count}/{max_posts_per_target})")

                try:
                    self.driver.execute_script("window.scrollBy(0, 300);")
                    self._random_pause(1, 2)

                    target_article, comment_box = self._find_next_comment_target()
                    if not target_article or not comment_box:
                        scroll_fails += 1
                        self._log("No eligible post found in the current viewport. Scrolling deeper.", "warning")
                        self.driver.execute_script("window.scrollBy(0, 800);")
                        self._random_pause(2, 3)
                        continue

                    scroll_fails = 0
                    self._mark_article_processed(target_article)
                    comment = self._generate_comment(comments)

                    self._log("Found a comment target. Typing the next queued comment.")
                    try:
                        comment_box.click()
                    except Exception:
                        pass
                    self._human_type(comment_box, comment)
                    self._random_pause(0.5, 1.5)
                    comment_box.send_keys(Keys.RETURN)

                    comment_count += 1
                    self._log(
                        f"Commented post {comment_count}/{max_posts_per_target}: {comment[:120]}",
                        "success",
                    )
                    self._log(f"Cooling down for about {delay_seconds} seconds before the next action.")
                    self._random_pause(delay_seconds, delay_seconds + 3)
                    self._check_stop()

                    self._dismiss_comment_overlay()
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'end'});",
                            target_article,
                        )
                    except Exception:
                        pass
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    self._random_pause(2, 3)
                except InterruptedError:
                    raise
                except Exception as exc:
                    scroll_fails += 1
                    self._log(f"Feed scan error: {exc}", "warning")
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    self._random_pause(2, 3)

            if comment_count >= max_posts_per_target:
                self._log(
                    f"Reached the per-target cap of {max_posts_per_target} comments for {target}.",
                    "success",
                )
            else:
                self._log(
                    f"Stopped scanning {target} after {scroll_fails} deep-scroll attempts without a match.",
                    "warning",
                )

        self._log("Job finished its queued browser actions.", "success")

    def cleanup(self) -> None:
        if self.driver:
            try:
                self.driver.service.stop()
            except Exception:
                pass
            self.driver = None
