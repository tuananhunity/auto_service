import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from src.utils.logger import GLOBAL_LOGGER

def setup_chrome_driver():
    """
    Sets up the Chrome WebDriver with options to mimic human browser behavior.
    """
    GLOBAL_LOGGER.info("====== WebDriver manager ======")
    try:
        chrome_data_dir = os.path.normpath(os.path.join(os.getcwd(), 'chrome_data'))
        if not os.path.exists(chrome_data_dir):
            os.makedirs(chrome_data_dir)

        chrome_options = Options()
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Tránh các flag bị máy chủ Facebook dễ nhận diện
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"user-data-dir={chrome_data_dir}")
        chrome_options.add_argument("--start-maximized")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Ẩn thuộc tính webdriver trên JS
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        GLOBAL_LOGGER.info("Chrome driver set up successfully.")
        return driver
    except Exception as e:
        GLOBAL_LOGGER.error(f"Failed to setup Chrome Driver: {e}")
        raise
