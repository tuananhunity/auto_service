import time
from selenium.webdriver.common.by import By
from src.core.browser import setup_chrome_driver

def scrape_joined_groups(log_callback=print):
    log_callback("Khởi động Browser để quét danh sách Nhóm...")
    driver = None
    groups_dict = {}
    try:
        driver = setup_chrome_driver()
        log_callback("Đang mở trang Facebook Groups...")
        driver.get("https://www.facebook.com/groups/")
        time.sleep(5)  # Chờ tải trang

        # Cuộn để tải thêm nhóm bên trái (Left Navigation) và trên Feed
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1.5)

        # Lấy tất cả link chứa đường dẫn tới groups
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/groups/')]")
        
        bad_keywords = ['category', 'discover', 'feed', 'joins', 'create', 'search']
        
        for link in links:
            try:
                url = link.get_attribute("href")
                if not url:
                    continue
                    
                text_raw = link.text.strip()
                # Lấy dòng đầu tiên nếu phần tử thẻ <a> chứa nhiều thẻ con (vd thông báo Nhóm mới)
                text = text_raw.split('\n')[0] if text_raw else None
                
                if text and "/groups/" in url:
                    # Kiểm tra bộ lọc từ cấm
                    if not any(bw in url.lower() for bw in bad_keywords):
                        parts = url.split("facebook.com/groups/")
                        if len(parts) > 1:
                            group_id = parts[1].split('/')[0] # UID hoặc Username của nhóm
                            if group_id and group_id.lower() not in bad_keywords:
                                # Loại bỏ các link phụ lạc loài, text phải đủ dài
                                if len(text) > 3:
                                    base_url = f"https://www.facebook.com/groups/{group_id}"
                                    # Chỉ lưu url duy nhất, tránh trùng lặp
                                    if base_url not in groups_dict:
                                        groups_dict[base_url] = text
                                        log_callback(f"[+] Tìm thấy: {text}")
            except Exception:
                pass
                
        log_callback(f"✅ Đã quét xong. Tổng cộng {len(groups_dict)} Nhóm hợp lệ.")
    except Exception as e:
        log_callback(f"❌ Lỗi khi quét nhóm: {e}")
    finally:
        if driver:
            driver.quit()
        
    return groups_dict
