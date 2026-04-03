import time
import random
from selenium.webdriver.common.action_chains import ActionChains

class HumanActionHelper:
    def __init__(self, driver):
        self.driver = driver

    def random_pause(self, min_time=1, max_time=5):
        """Pauses execution for a random duration to mimic human reading speed."""
        time.sleep(random.uniform(min_time, max_time))

    def random_scroll(self):
        """Scrolls the page randomly to simulate reading."""
        scroll_amount = random.randint(300, 800)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self.random_pause(1, 4)
        if random.random() > 0.5:
            # Scroll back up a little bit
            self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount // 2});")
            self.random_pause(1, 3)

    def human_mouse_jiggle(self, element, moves=3):
        """Jiggles the mouse around the element before clicking."""
        try:
            action = ActionChains(self.driver)
            for _ in range(moves):
                x_offset = random.randint(-5, 5)
                y_offset = random.randint(-5, 5)
                action.move_to_element_with_offset(element, x_offset, y_offset)
                action.pause(random.uniform(0.1, 0.4))
            action.perform()
        except Exception:
            pass

    def human_type(self, element, text: str):
        """Types text character by character with random delays and occasional typos."""
        for char in text:
            element.send_keys(char)
            # 5% chance to make a typo and correct it
            if random.random() < 0.05:
                wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                element.send_keys(wrong_char)
                time.sleep(random.uniform(0.05, 0.15))
                element.send_keys('\b') # Backspace
            
            # Random delay between keystrokes (50ms to 250ms)
            time.sleep(random.uniform(0.05, 0.25))
