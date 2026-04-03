import customtkinter as ctk
from tkinter import filedialog
import threading
import os

from src.core.facebook_bot import FacebookBot
from src.core.group_scraper import scrape_joined_groups
from src.utils.file_parser import load_lines_from_file

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Facebook Auto Comment - Multi Group Pro")
        self.geometry("850x800")
        
        # Grid config
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1) # Cột danh sách nhóm phình ra
        self.grid_rowconfigure(5, weight=1) # Cột logs phình ra
        
        # Title
        self.label_title = ctk.CTkLabel(self, text="Facebook Auto Bot Pro", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_title.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10))
        
        # Group list frame
        self.frame_group = ctk.CTkFrame(self)
        self.frame_group.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="nsew")
        self.frame_group.grid_columnconfigure(0, weight=1)
        self.frame_group.grid_rowconfigure(1, weight=1)
        
        self.label_group = ctk.CTkLabel(self.frame_group, text="Danh sách Nhóm mục tiêu (Facebook Groups):", font=ctk.CTkFont(weight="bold"))
        self.label_group.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.btn_fetch_groups = ctk.CTkButton(self.frame_group, text="🔄 Quét Auto từ FB", width=140, fg_color="#3b5998", hover_color="#2d4373", command=self.fetch_groups_thread)
        self.btn_fetch_groups.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        self.scrollable_groups = ctk.CTkScrollableFrame(self.frame_group, height=180)
        self.scrollable_groups.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        self.checkboxes = [] # List to hold tuples: (CTkCheckBox ref, URL string)
        
        self.btn_import_groups = ctk.CTkButton(self.frame_group, text="📁 Hoặc Tải từ File TXT...", width=140, command=self.import_groups_file)
        self.btn_import_groups.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        # Comments file
        self.label_comment = ctk.CTkLabel(self, text="Comments File (*.txt):")
        self.label_comment.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        self.entry_comment = ctk.CTkEntry(self, placeholder_text="Đường dẫn file chứa bình luận...")
        self.entry_comment.grid(row=2, column=1, padx=(0, 10), pady=10, sticky="ew")
        
        self.btn_browse_comment = ctk.CTkButton(self, text="Chọn File", width=100, command=self.browse_comment_file)
        self.btn_browse_comment.grid(row=2, column=2, padx=20, pady=10)
        
        # Settings frame
        self.frame_settings = ctk.CTkFrame(self)
        self.frame_settings.grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.frame_settings.grid_columnconfigure(1, weight=1)
        self.frame_settings.grid_columnconfigure(3, weight=1)
        
        self.label_max = ctk.CTkLabel(self.frame_settings, text="Số bài / Nhóm:")
        self.label_max.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_max = ctk.CTkEntry(self.frame_settings, width=80)
        self.entry_max.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        self.entry_max.insert(0, "5")
        
        self.label_delay = ctk.CTkLabel(self.frame_settings, text="Delay (giây):")
        self.label_delay.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.entry_delay = ctk.CTkEntry(self.frame_settings, width=80)
        self.entry_delay.grid(row=0, column=3, padx=10, pady=10, sticky="w")
        self.entry_delay.insert(0, "7")
        
        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.btn_start = ctk.CTkButton(self.btn_frame, text="▶ Bắt đầu chạy", command=self.start_bot, fg_color="green", hover_color="darkgreen", font=ctk.CTkFont(weight="bold"))
        self.btn_start.pack(side="left", padx=10)
        
        self.btn_stop = ctk.CTkButton(self.btn_frame, text="⏹ Dừng khẩn cấp", command=self.stop_bot, fg_color="red", hover_color="darkred", state="disabled", font=ctk.CTkFont(weight="bold"))
        self.btn_stop.pack(side="left", padx=10)
        
        # Logs (row 5)
        self.textbox_log = ctk.CTkTextbox(self, state="disabled", font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_log.grid(row=5, column=0, columnspan=3, padx=20, pady=(10, 5), sticky="nsew")
        
        # Footer
        self.label_footer = ctk.CTkLabel(self, text="Author: soikhongngu", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.label_footer.grid(row=6, column=0, columnspan=3, pady=(0, 10))
        
        # State
        self.bot_thread = None
        self.bot_instance = None
        self.stop_event = threading.Event()

        # Init with default files if exist
        if os.path.exists("comments.txt"):
            self.entry_comment.insert(0, os.path.abspath("comments.txt"))
        if os.path.exists("groups.txt"):
            self.load_groups_to_ui(load_lines_from_file("groups.txt"))
            
    def _write_log(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", message + "\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def log(self, message):
        self.after(0, self._write_log, message)
        
    def import_groups_file(self):
        filepath = filedialog.askopenfilename(title="Chọn file txt chứa link Nhóm (mỗi link 1 dòng)", filetypes=[("Text Files", "*.txt")])
        if filepath:
            urls = load_lines_from_file(filepath)
            self.load_groups_to_ui(urls)
            self.log(f"Đã tải {len(urls)} nhóm từ file lên UI.")

    def fetch_groups_thread(self):
        self.btn_fetch_groups.configure(state="disabled")
        threading.Thread(target=self._run_fetching, daemon=True).start()

    def _run_fetching(self):
        groups_dict = scrape_joined_groups(log_callback=self.log)
        if groups_dict:
            # Chuyển dict sang UI (cần dùng after vì đang ở thread fụ)
            self.after(0, self.render_groups_dict, groups_dict)
        self.after(0, lambda: self.btn_fetch_groups.configure(state="normal"))

    def render_groups_dict(self, groups_dict):
        # Clear existing
        for cb, url in self.checkboxes:
            cb.destroy()
        self.checkboxes.clear()
        
        # Render
        for idx, (url, name) in enumerate(groups_dict.items()):
            cb_text = f"{name} ({url.replace('https://www.facebook.com/groups/','')})"
            cb = ctk.CTkCheckBox(self.scrollable_groups, text=cb_text)
            cb.grid(row=idx, column=0, padx=5, pady=5, sticky="w")
            cb.select() # Chọn sẵn mặc định
            self.checkboxes.append((cb, url))

    def load_groups_to_ui(self, list_urls):
        # Clear existing
        for cb, url in self.checkboxes:
            cb.destroy()
        self.checkboxes.clear()
        
        for idx, url in enumerate(list_urls):
            cb = ctk.CTkCheckBox(self.scrollable_groups, text=url)
            cb.grid(row=idx, column=0, padx=5, pady=5, sticky="w")
            cb.select()
            self.checkboxes.append((cb, url))
            
    def browse_comment_file(self):
        filepath = filedialog.askopenfilename(title="Chọn file txt danh sách bình luận", filetypes=[("Text Files", "*.txt")])
        if filepath:
            self.entry_comment.delete(0, "end")
            self.entry_comment.insert(0, filepath)
            
    def run_bot_thread(self, group_urls, comments_list, config):
        try:
            self.bot_instance = FacebookBot(
                group_urls=group_urls,
                comments_list=comments_list,
                config=config,
                log_callback=self.log,
                stop_event=self.stop_event
            )
            self.bot_instance.run()
        except Exception as e:
            if "Stopped by User" not in str(e):
                self.log(f"💥 Lỗi nghiêm trọng: {e}")
        finally:
            self.after(0, self.reset_ui)
            
    def start_bot(self):
        group_urls = [url for cb, url in self.checkboxes if cb.get() == 1]
        comment_file = self.entry_comment.get().strip()
        max_posts = self.entry_max.get().strip()
        delay = self.entry_delay.get().strip()
        
        if not group_urls:
            self.log("❌ Bạn chưa Tick chọn bất kỳ Group nào trong danh sách!")
            return
            
        comments_list = []
        if comment_file and os.path.exists(comment_file):
            comments_list = load_lines_from_file(comment_file)
            
        custom_config = {
            'MAX_POSTS_PER_GROUP': int(max_posts) if max_posts.isdigit() else 5,
            'DELAY': int(delay) if delay.isdigit() else 5
        }
        
        self.stop_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        
        self.log("="*40)
        self.log(f"🚀 BẮT ĐẦU CHIẾN DỊCH: {len(group_urls)} Nhóm")
        self.log("="*40)
        
        self.bot_thread = threading.Thread(
            target=self.run_bot_thread, 
            args=(group_urls, comments_list, custom_config), 
            daemon=True
        )
        self.bot_thread.start()
        
    def stop_bot(self):
        self.log("⚠️ Đang gửi lệnh dừng khẩn cấp... Vui lòng đợi trình duyệt đóng.")
        self.stop_event.set()
        
        if self.bot_instance and self.bot_instance.driver:
            try:
                self.bot_instance.driver.quit()
            except:
                pass
        
    def reset_ui(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

def run_app():
    app = MainWindow()
    app.mainloop()
