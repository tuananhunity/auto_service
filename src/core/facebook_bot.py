import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from src.core.browser import setup_chrome_driver
from src.core.human_actions import HumanActionHelper

class FacebookBot:
    def __init__(self, group_urls, comments_list, config, log_callback, stop_event):
        self.group_urls = group_urls
        self.comments_list = comments_list
        self.config = config
        self.log_callback = log_callback
        self.stop_event = stop_event
        self.driver = None
        self.helper = None

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def generate_comment(self) -> str:
        if not self.comments_list:
            return "Tuyệt vời!"
        return random.choice(self.comments_list)

    def check_stop(self):
        if self.stop_event.is_set():
            self._log("⚠️ Tiến trình bị dừng khẩn cấp bởi người dùng!")
            raise InterruptedError("Stopped by User")

    def run(self):
        try:
            self.driver = setup_chrome_driver()
            self.helper = HumanActionHelper(self.driver)
            
            # Khởi động trình duyệt, mở trang Google trước để test mạng
            self.driver.get("https://www.google.com")
            self._log("Khởi động Browser hoàn tất. Chuẩn bị chạy chiến dịch...")
            
            max_posts_per_group = int(self.config.get('MAX_POSTS_PER_GROUP', 5))
            delay_seconds = int(self.config.get('DELAY', 5))
            comment_box_xpath = self.config.get('COMMENT_BOX_XPATH', "//div[(contains(@aria-label, 'Write a comment') or contains(@aria-label, 'Viết bình luận') or contains(@aria-label, 'Bình luận công khai')) and @contenteditable='true']")

            for group_url in self.group_urls:
                self.check_stop()
                self._log(f"\n====================================\nĐang vào Nhóm: {group_url}")
                self.driver.get(group_url.strip())
                self.helper.random_pause(5, 10)
                
                comment_count = 0
                max_scroll_attempts = 15
                scroll_fails = 0

                while comment_count < max_posts_per_group and scroll_fails < max_scroll_attempts:
                    self.check_stop()
                    self._log(f"Đang quét bài viết mới. (Đã xử lý: {comment_count}/{max_posts_per_group})")
                    
                    self.driver.execute_script("window.scrollBy(0, 300);")
                    self.helper.random_pause(2, 3)
                    
                    found_target = None
                    target_article = None
                    
                    try:
                        articles = self.driver.find_elements(By.XPATH, "//div[@role='article']")
                        
                        for article in articles:
                            self.check_stop()
                            if article.get_attribute("data-bot-commented") == "true":
                                continue
                                
                            if article.is_displayed():
                                target_article = article
                                
                                # Cố tìm xem bài viết này CÓ SẴN ô nhập chữ không
                                try:
                                    boxes = article.find_elements(By.XPATH, "." + comment_box_xpath)
                                    for b in boxes:
                                        if b.is_displayed():
                                            found_target = b
                                            break
                                except:
                                    pass
                                    
                                if found_target:
                                    break
                                    
                                # Nếu KHÔNG CÓ SẴN ô chữ, đi tìm Nút/Icon Bình luận
                                xpath_btns = ".//*[(@role='button' or @tabindex='0' or @role='link') and (contains(translate(@aria-label, 'BCMNL', 'bcmnl'), 'comment') or contains(translate(@aria-label, 'BCMNL', 'bcmnl'), 'bình luận') or contains(translate(., 'BCMNL', 'bcmnl'), 'comment') or contains(translate(., 'BCMNL', 'bcmnl'), 'bình luận'))]"
                                btns = article.find_elements(By.XPATH, xpath_btns)
                                valid_btn = None
                                bad_words = ["nhãn dán", "gif", "avatar", "sticker", "file đính kèm", "attachment", "mới", "xem thêm"]
                                
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
                                    self._log("Đã tìm thấy bài chưa bình luận. Đang click mở hộp thoại...")
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", valid_btn)
                                    self.helper.random_pause(1, 2)
                                    try:
                                        self.helper.human_mouse_jiggle(valid_btn, moves=2)
                                        valid_btn.click()
                                    except:
                                        self.driver.execute_script("arguments[0].click();", valid_btn)
                                        
                                    self.helper.random_pause(1, 2)
                                    
                                    active_el = self.driver.switch_to.active_element
                                    if active_el and (active_el.get_attribute("contenteditable") == "true" or active_el.tag_name in ['input', 'textarea']):
                                        found_target = active_el
                                        break
                                    else:
                                        global_boxes = self.driver.find_elements(By.XPATH, comment_box_xpath)
                                        for gb in global_boxes:
                                            if gb.is_displayed():
                                                found_target = gb
                                                break
                                        if found_target:
                                            break
                                            
                                # Không tìm được gì => Đánh dấu bỏ qua
                                self.driver.execute_script("arguments[0].setAttribute('data-bot-commented', 'true');", target_article)
                                
                        if found_target and target_article:
                            scroll_fails = 0 # Reset fails since we found something
                            self.driver.execute_script("arguments[0].setAttribute('data-bot-commented', 'true');", target_article)
                            
                            comment = self.generate_comment()
                            self.helper.human_type(found_target, comment)
                            self.helper.random_pause(0.5, 1.5)
                            found_target.send_keys(Keys.RETURN)
                            
                            comment_count += 1
                            self._log(f"✅ Đã bình luận thành công bài {comment_count}/{max_posts_per_group}: '{comment}'")
                            self._log(f"Đang nghỉ {delay_seconds} giây an toàn...")
                            self.helper.random_pause(delay_seconds, delay_seconds + 3)
                            self.check_stop()
                            
                            # Tắt Popup
                            try:
                                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                                time.sleep(0.5)
                                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                                time.sleep(1)
                            except:
                                pass
                                
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", target_article)
                            self.driver.execute_script("window.scrollBy(0, 500);")
                            time.sleep(3)
                        else:
                            scroll_fails += 1
                            self._log("Chưa thấy bài viết hợp lệ, đang cuộn xuống...")
                            self.driver.execute_script("window.scrollBy(0, 800);")
                            time.sleep(3)
                    except InterruptedError:
                        raise
                    except Exception as e:
                        self._log(f"Lỗi khi xử lý News Feed: {e}")
                        self.driver.execute_script("window.scrollBy(0, 500);")
                        time.sleep(3)
                        scroll_fails += 1
                        
                if comment_count >= max_posts_per_group:
                    self._log(f"🎉 Hoàn thành giới hạn {max_posts_per_group} bài cho nhóm này.")
                else:
                    self._log(f"⚠️ Dừng nhóm này vì lướt quá sâu không thấy bài mới ({scroll_fails} fails).")

            self._log("\n🚀 CHIẾN DỊCH HOÀN TẤT CHO TẤT CẢ CÁC NHÓM!")
            
        except InterruptedError:
            pass # Ném ra do người dùng Pause/Stop
        except Exception as e:
            self._log(f"❌ Bot bị lỗi treo máy: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self._log("Browser đã được đóng.")
