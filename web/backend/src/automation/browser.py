from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def attach_to_debug_port(
    debug_port: int,
    chrome_binary_path: str | None = None,
    driver_binary_path: str | None = None,
) -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    if chrome_binary_path:
        options.binary_location = chrome_binary_path

    service = Service(driver_binary_path or ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)
