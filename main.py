import os
import random
import time
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException
)
from webdriver_manager.chrome import ChromeDriverManager
import os
from dotenv import load_dotenv

load_dotenv()

def load_comments(filepath="comments.txt"):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Lỗi khi đọc file {filepath}: {e}")
        return ["Bài viết rất hay, cảm ơn bạn đã chia sẻ!"]
CONFIG = {
    'POST_URL': os.getenv('POST_URL'),
    # Hỗ trợ cả tiếng Anh và tiếng Việt cho ô nhập chữ
    'COMMENT_BOX_XPATH': "//div[(contains(@aria-label, 'Write a comment') or contains(@aria-label, 'Viết bình luận') or contains(@aria-label, 'Bình luận dưới tên') or contains(@aria-label, 'Bình luận công khai')) and @contenteditable='true']",
    'MAX_COMMENTS': 100,
    'MAX_ITERATIONS': 10000,
    'DELAYS': {
        'SHORT_MIN': 0.5,
        'SHORT_MAX': 2.0,
        'MEDIUM_MIN': 1,
        'MEDIUM_MAX': 3,
        'LONG_MIN': 5,
        'LONG_MAX': 20,
        'RELOAD_PAUSE': 180,
    },
    'CHROME_PROFILE': 'Default'
}

COMMENTS_LIST = load_comments('comments.txt')

def setup_logger():
    """
    Set up comprehensive logging configuration.
    """
    os.makedirs('logs', exist_ok=True)
    log_filename = f'logs/facebook_comment_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

class FacebookAICommentBot:
    def __init__(self, config=None, log_callback=None):
        """
        Initialize the Facebook comment bot with configuration.
        """
        self.config = {**CONFIG, **(config or {})}
        self.driver = None
        self.log_callback = log_callback

    def _log(self, msg, level='info'):
        if level == 'info':
            logger.info(msg)
        elif level == 'error':
            logger.error(msg)
        elif level == 'warning':
            logger.warning(msg)
        elif level == 'critical':
            logger.critical(msg)
        else:
            logger.debug(msg)
        
        if self.log_callback:
            self.log_callback(msg)

    def setup_driver(self):
        """
        Sets up and configures the Selenium WebDriver.
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Set Chrome binary location (adjust as needed)
            # chrome_options.binary_location = "C:/Program Files/Google/Chrome/Application/chrome.exe"

            # Create a custom user-data dir (so we don't need your real profile path)
            user_data_dir = os.path.join(os.getcwd(), "chrome_data")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument(f"--profile-directory={self.config['CHROME_PROFILE']}")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self._log("Chrome driver set up successfully.")
        except Exception as e:
            self._log(f"Failed to setup Chrome Driver: {e}", 'error')
            raise

    def random_pause(self, min_time=1, max_time=5):
        """
        Pause execution for a random duration between min_time and max_time seconds.
        """
        delay = random.uniform(min_time, max_time)
        time.sleep(delay)
        logger.debug(f"Paused for {delay:.2f} seconds.")

    def human_mouse_jiggle(self, element, moves=2):
        """
        Simulate human-like mouse movements over a given element.

        Args:
            element: The web element to move the mouse over.
            moves: Number of jiggle movements.
        """
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()

            for _ in range(moves):
                x_offset = random.randint(-15, 15)
                y_offset = random.randint(-15, 15)
                actions.move_by_offset(x_offset, y_offset).perform()
                self.random_pause(0.3, 1)

            # Return to the element
            actions.move_to_element(element).perform()
            self.random_pause(0.3, 1)
            logger.debug(f"Performed mouse jiggle with {moves} moves.")
        except Exception as e:
            logger.error(f"Mouse jiggle failed: {e}")

    def human_type(self, element, text):
        """
        Simulate human-like typing into a web element.

        Args:
            element: The web element to type into.
            text: The text to type.
        """
        words = text.split()
        for w_i, word in enumerate(words):
            # Introduce random fake words
            if random.random() < 0.05:
                fake_word = random.choice(["aaa", "zzz", "hmm"])
                for c in fake_word:
                    element.send_keys(c)
                    time.sleep(random.uniform(0.08, 0.35))
                for _ in fake_word:
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.06, 0.25))

            for char in word:
                if random.random() < 0.05:
                    wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                    element.send_keys(wrong_char)
                    time.sleep(random.uniform(0.08, 0.35))
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.06, 0.25))
                element.send_keys(char)
                time.sleep(random.uniform(0.08, 0.35))

            if w_i < len(words) - 1:
                element.send_keys(" ")
                time.sleep(random.uniform(0.08, 0.3))

            # random cursor movements
            if random.random() < 0.03:
                element.send_keys(Keys.ARROW_LEFT)
                time.sleep(random.uniform(0.1, 0.3))
                element.send_keys(Keys.ARROW_RIGHT)
                time.sleep(random.uniform(0.1, 0.3))

        self.random_pause(0.5, 1.5)
        logger.debug("Completed human-like typing.")

    def random_scroll(self):
        """
        Scroll up/down randomly to mimic a user's reading or browsing.
        """
        scroll_direction = random.choice(["up", "down"])
        scroll_distance = random.randint(200, 800)

        if scroll_direction == "down":
            self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            logger.debug(f"Scrolling down {scroll_distance} pixels.")
        else:
            self.driver.execute_script(f"window.scrollBy(0, -{scroll_distance});")
            logger.debug(f"Scrolling up {scroll_distance} pixels.")

        self.random_pause(1, 3)

    def random_hover_or_click(self):
        """
        Randomly hover or click on some links or elements on the page to mimic user exploration.
        """
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        if not all_links:
            return

        if random.random() < 0.5:
            random_link = random.choice(all_links)
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(random_link).perform()
                logger.debug("Hovering over a random link.")
                self.random_pause(1, 3)

                if random.random() < 0.2:
                    random_link.click()
                    logger.debug("Clicked a random link. Going back in 3 seconds.")
                    time.sleep(3)
                    self.driver.back()
                    self.random_pause(1, 3)
            except Exception as e:
                logger.debug(f"Random hover/click failed: {e}")

    def generate_comment(self) -> str:
        """
        Lấy một bình luận ngẫu nhiên từ danh sách (comments.txt) thay vì dùng AI.
        """
        try:
            comment = random.choice(COMMENTS_LIST)
            self._log(f"Selected comment: {comment}", 'debug')
            return comment
        except Exception as e:
            self._log(f"Lỗi khi chọn bình luận: {e}", 'error')
            return "Bài viết rất hay và ý nghĩa!"

    def run(self):
        """
        Main method to execute the Facebook group comment bot with human-like actions.
        """
        try:
            self.setup_driver()
            url = self.config.get('POST_URL', '')
            self._log(f"Đang tải trang: {url}")
            self.driver.get(url)
            
            # Cho người dùng 10 giây ban đầu để xem hoặc đăng nhập nếu cần
            self._log(f"Chờ 10 giây để tải trang / đăng nhập...")
            time.sleep(10)

            comment_count = 0
            max_comments = int(self.config.get('MAX_COMMENTS', 10))
            delay_seconds = int(self.config.get('DELAY_SECONDS', 10))

            for i in range(self.config['MAX_ITERATIONS']):
                if comment_count >= max_comments:
                    self._log("Đã đạt mốc giới hạn bình luận tối đa.")
                    break

                self._log("Đang quét các bài viết trên News Feed...")
                try:
                    self.driver.execute_script("window.scrollBy(0, 300);")
                    self.random_pause(1, 2)
                    
                    found_target = None
                    target_article = None
                    
                    # Cách phân tích bài viết chính xác nhất là: Tìm từng khối bài viết (<div role='article'>)
                    articles = self.driver.find_elements(By.XPATH, "//div[@role='article']")
                    
                    for article in articles:
                        if article.get_attribute("data-bot-commented") == "true":
                            continue
                            
                        # Đã tìm thấy một bài viết chưa bình luận
                        if article.is_displayed():
                            target_article = article
                            
                            # Cố tìm xem bài viết này CÓ SẴN ô nhập chữ không (Dạng mở rộng sẵn)
                            try:
                                xpath_box = "." + self.config['COMMENT_BOX_XPATH']
                                boxes = article.find_elements(By.XPATH, xpath_box)
                                for b in boxes:
                                    if b.is_displayed():
                                        found_target = b
                                        break
                            except:
                                pass
                                
                            if found_target:
                                break # Đã tìm thấy ô để gõ
                                
                            # Nếu KHÔNG CÓ SẴN ô chữ, đi tìm Nút/Icon Bình luận
                            xpath_btns = ".//*[(@role='button' or @tabindex='0' or @role='link') and (contains(translate(@aria-label, 'BCMNL', 'bcmnl'), 'comment') or contains(translate(@aria-label, 'BCMNL', 'bcmnl'), 'bình luận') or contains(translate(., 'BCMNL', 'bcmnl'), 'comment') or contains(translate(., 'BCMNL', 'bcmnl'), 'bình luận'))]"
                            btns = article.find_elements(By.XPATH, xpath_btns)
                            
                            valid_btn = None
                            bad_words = ["nhãn dán", "gif", "avatar", "sticker", "file đính kèm", "attachment", "mới nhất", "bình luận trước"]
                            for btn in btns:
                                if btn.is_displayed():
                                    try:
                                        text = btn.text.lower()
                                        aria = (btn.get_attribute("aria-label") or "").lower()
                                        combined = text + " " + aria
                                        if ("bình luận" in combined or "comment" in combined) and not any(bad in combined for bad in bad_words):
                                            if len(text) < 50:
                                                valid_btn = btn
                                                break
                                    except:
                                        pass
                                        
                            if valid_btn:
                                # Click vào nút đó để mở Popup hoặc xổ ô bình luận ra
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", valid_btn)
                                self.random_pause(1, 2)
                                try:
                                    self.human_mouse_jiggle(valid_btn, moves=2)
                                    valid_btn.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", valid_btn)
                                    
                                self.random_pause(1, 2)
                                
                                # Tìm lại ô nhập chữ sau khi nó xổ ra
                                active_el = self.driver.switch_to.active_element
                                if active_el and (active_el.get_attribute("contenteditable") == "true" or active_el.tag_name in ['input', 'textarea']):
                                    found_target = active_el
                                    break
                                else:
                                    # Tìm rộng trên trang (trường hợp nó bật bung popup che màn hình)
                                    global_boxes = self.driver.find_elements(By.XPATH, self.config['COMMENT_BOX_XPATH'])
                                    for gb in global_boxes:
                                        if gb.is_displayed():
                                            found_target = gb
                                            break
                                    if found_target:
                                        break
                                        
                            # Dù bài viết này lỗi không tìm được nút hay ô, cũng đánh dấu bỏ qua để khỏi kẹt
                            self.driver.execute_script("arguments[0].setAttribute('data-bot-commented', 'true');", target_article)
                    
                    if found_target and target_article:
                        self.driver.execute_script("arguments[0].setAttribute('data-bot-commented', 'true');", target_article)
                        self._log("Bắt đầu tự động nhập bình luận...")
                        
                        comment = self.generate_comment()
                        self.human_type(found_target, comment)
                        self.random_pause(0.5, 1.5)
                        found_target.send_keys(Keys.RETURN)
                        
                        comment_count += 1
                        self._log(f"✅ Đã bình luận thành công: '{comment}'")
                        self._log(f"Nghỉ ngơi {delay_seconds} tiếp tục...")
                        self.random_pause(delay_seconds, delay_seconds + 3)
                        
                        # Thoát Popup
                        try:
                            webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(0.5)
                            webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(1)
                        except:
                            pass
                            
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", target_article)
                        self.driver.execute_script("window.scrollBy(0, 500);")
                        time.sleep(3)
                    else:
                        self._log("Chưa thấy bài viết hợp lệ, đang cuộn xuống...")
                        self.driver.execute_script("window.scrollBy(0, 800);")
                        time.sleep(5)
                        
                except Exception as e:
                    self._log(f"Lỗi vòng lặp quét bài: {e}", 'warning')
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(3)
        except Exception as e:
            self._log(f"Bot execution bị lỗi: {e}", 'critical')
        finally:
            if self.driver:
                self.driver.quit()
                self._log("Browser đã được đóng.")

def main():
    """
    Main function for the Facebook comment bot.
    """
    try:
        bot = FacebookAICommentBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Bot initialization failed: {e}")

if __name__ == "__main__":
    main()
