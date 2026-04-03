import customtkinter as ctk
import threading
import sys
from main import FacebookAICommentBot, CONFIG

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Facebook Auto Comment Bot - Group Edition")
        self.geometry("700x600")
        
        # Grid config
        self.grid_columnconfigure(1, weight=1)
        
        # UI Elements
        self.label_title = ctk.CTkLabel(self, text="Facebook Auto Comment Bot", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_title.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))
        
        # URL
        self.label_url = ctk.CTkLabel(self, text="Group/Post URL:")
        self.label_url.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        self.entry_url = ctk.CTkEntry(self, placeholder_text="https://www.facebook.com/groups/...")
        self.entry_url.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        
        # Max Comments
        self.label_max = ctk.CTkLabel(self, text="Max Posts:")
        self.label_max.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        self.entry_max = ctk.CTkEntry(self, placeholder_text="10")
        self.entry_max.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        self.entry_max.insert(0, "10")
        
        # Delay
        self.label_delay = ctk.CTkLabel(self, text="Delay (seconds):")
        self.label_delay.grid(row=3, column=0, padx=20, pady=10, sticky="w")
        
        self.entry_delay = ctk.CTkEntry(self, placeholder_text="5")
        self.entry_delay.grid(row=3, column=1, padx=20, pady=10, sticky="ew")
        self.entry_delay.insert(0, "5")
        
        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.btn_start = ctk.CTkButton(self.btn_frame, text="Start Bot", command=self.start_bot, fg_color="green", hover_color="darkgreen")
        self.btn_start.pack(side="left", padx=10)
        
        self.btn_stop = ctk.CTkButton(self.btn_frame, text="Force Stop", command=self.stop_bot, fg_color="red", hover_color="darkred", state="disabled")
        self.btn_stop.pack(side="left", padx=10)
        
        # Logs
        self.textbox_log = ctk.CTkTextbox(self, height=200, state="disabled")
        self.textbox_log.grid(row=5, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        self.grid_rowconfigure(5, weight=1)
        
        self.bot_thread = None
        self.bot_instance = None
        
    def write_log(self, message):
        # Update UI text safely from another thread
        self.after(0, self._write_log, message)
        
    def _write_log(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", message + "\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def run_bot_thread(self, config):
        try:
            self.bot_instance = FacebookAICommentBot(config=config, log_callback=self.write_log)
            self.bot_instance.run()
        except Exception as e:
            self.write_log(f"Bot crashed: {e}")
        finally:
            self.after(0, self.reset_ui)
            
    def start_bot(self):
        url = self.entry_url.get().strip()
        max_posts = self.entry_max.get().strip()
        delay = self.entry_delay.get().strip()
        
        if not url:
            self.write_log("❌ Vui lòng nhập URL.")
            return
            
        custom_config = {
            'POST_URL': url,
            'MAX_COMMENTS': int(max_posts) if max_posts.isdigit() else 10,
            'DELAY_SECONDS': int(delay) if delay.isdigit() else 5
        }
        
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.write_log(f"🚀 Bắt đầu khởi chạy Bot cho URL: {url}...")
        
        self.bot_thread = threading.Thread(target=self.run_bot_thread, args=(custom_config,), daemon=True)
        self.bot_thread.start()
        
    def stop_bot(self):
        self.write_log("⚠️ Dang yêu cầu dừng...")
        if self.bot_instance and self.bot_instance.driver:
            try:
                self.bot_instance.driver.quit()
                self.bot_instance.driver = None
            except:
                pass
        self.reset_ui()
        
    def reset_ui(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

if __name__ == "__main__":
    app = App()
    app.mainloop()
