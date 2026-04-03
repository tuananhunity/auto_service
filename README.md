# 📢 Bot Tự Động Bình Luận Facebook (Có Giao Diện)

Chương trình này là một công cụ tự động hóa hành vi rảnh tay (Browser Automation) sử dụng **Selenium**, được thiết kế để tự động bình luận trên nền tảng Facebook (hỗ trợ cả bài viết cá nhân lẫn bài viết trong Hội Nhóm/Group). 

Đặc biệt, công cụ này đã được **vô hiệu hóa việc trích xuất token OpenAI tốn phí**, và thay vào đó lấy bình luận trực tiếp từ file văn bản tĩnh trên máy bạn để hoàn toàn **miễn phí 100%**.

---

## 🌟 Tại sao không cần Token? (Giải thích luồng hoạt động)

Phần lớn các tool bot trên mạng yêu cầu **Access Token** hoặc **Cookie** qua API để gửi request tới máy chủ Facebook. Tuy nhiên, cách đó rất dễ bị Facebook khóa tài khoản (Check-point) vì nó phát hiện ra hành vi bất thường của máy móc.

Tool này hoạt động theo mô hình **Ngụy trang con người (Human Like Simulation)**:
1. Nó **Mở một trình duyệt Google Chrome thật sự** lên màn hình.
2. Nó tái sử dụng chính tài khoản Facebook bạn đã đăng nhập để lướt web (không lấy cắp Cookie gửi lên mạng). Bạn chỉ việc đăng nhập một lần bằng tay, trình duyệt sẽ lưu phiên đăng nhập đó vào thư mục `chrome_data` nằm trên máy tính của bạn.
3. Nó **tự động phân tích màn hình** trang Facebook, tìm xem ô gõ bình luận nằm ở đâu.
4. Nó tự tạo ra thao tác **di chuyển chuột**, click chuột giống tay người.
5. Nó lấy các câu lập trình sẵn từ file text, sau đó **nhập từng ký tự một** với tốc độ chập chờn (cố tình gõ sai rồi xóa đi gõ lại) giống y hệt một người dùng bình thường đang ngồi ấn phím.
6. Sau khi Enter, nó sẽ cuộn chuột xuống bài đăng tiếp theo của Hội Nhóm và lặp lại vòng lặp.

Nhờ việc bắt chước thao tác người thật như vậy, bạn **không cần thao tác Token phức tạp** nào cả mà vẫn vượt qua được các chốt chặn phát hiện Bot của nền tảng web.

---

## 🛠️ Hướng dẫn sử dụng

### 1. Chuẩn bị nội dung bình luận
Mở file `comments.txt` nằm chung thư mục. Hãy nhập vào tất cả các câu bình luận mà bạn muốn bot tự động gõ. 
Mỗi bình luận viết trên 1 dòng. Tool sẽ chọn ngẫu nhiên một dòng để bình luận vào giao diện.

### 2. Khởi chạy Ứng dụng
Bạn đã cài đặt xong môi trường, từ giờ bạn chỉ cần mở Terminal và gõ:
```bash
python3 gui.py
```
> Lúc này cửa sổ **tối màu (Dark Mode)** của ứng dụng sẽ xuất hiện.

### 3. Thiết lập thông số & Chạy
- **Group/Post URL:** Dán link của Nhóm (Group) hoặc Bài viết (Post) mà bạn muốn thả bình luận.
- **Max Posts:** Giới hạn tổng số lượng bài viết mà script sẽ cày (Ví dụ: 10 bài là ngưng).
- **Delay:** Thời gian nghỉ ngơi để uống nước giữa 2 bài liên tiếp (Nên để 5-10 giây để an toàn).
- **Bắt đầu (Start Bot):** Nhấn nút này lúc đã sẵn sàng.

> **LƯU Ý LẦN ĐẦU TIÊN CHẠY:**
> Khi Trình duyệt web tự động hiện lên, nếu Facebook yêu cầu, hãy tự động gõ mật khẩu đăng nhập Facebook của bạn vào trình duyệt. Sau khi đăng nhập xong, bot sẽ nạp lại trang và bắt đầu đi "spam dạo". Các lần chạy lại hôm sau bạn không cần đăng nhập nữa.

---

## ⚠️ Lưu ý an toàn
Mặc dù công cụ được tối ưu chống Bot (Anti-detect), nhưng nếu bạn thiết lập bình luận **quá nhanh** (delay siêu ngắn) hay thiết lập **quá nhiều** (Max Post: 1000) trong thời gian ngắn, hệ thống AI đo lường tần suất của Facebook vẫn có thể tạm thời khóa mõm (Block Comment) của tài khoản bạn vài ngày do vi phạm Tiêu chuẩn Cộng đồng. Hãy thiết lập một cách từ từ và có khoa học!
---

## 📱 Điều khiển từ xa (Web & Mobile)

Bản cập nhật mới hỗ trợ điều khiển Bot từ xa thông qua giao diện Web và ứng dụng điện thoại Android.

### 1. Khởi chạy Backend (trên Máy tính)
Để các giao diện từ xa hoạt động, bạn cần chạy Flask server trên máy tính (nơi đang chạy Bot):
```bash
python3 server.py
```
*Giao diện Web sẽ mặc định chạy tại: `http://localhost:5000`*

### 2. Giao diện Web Dashboard
Bạn có thể mở trình duyệt trên máy tính hoặc điện thoại (cùng mạng WiFi) để truy cập vào địa chỉ IP của máy tính:
- Tại máy: `http://localhost:5000`
- Thiết bị khác: `http://<IP-MÁY-TÍNH>:5000`

### 3. Ứng dụng Android (Mobile App)
Ứng dụng được xây dựng bằng Expo (React Native).

**Chạy qua Expo Go (Để test nhanh):**
1. Cài đặt ứng dụng **Expo Go** trên điện thoại từ Play Store.
2. Tại máy tính, di chuyển vào thư mục mobile và chạy:
   ```bash
   cd mobile
   npm install
   npx expo start
   ```
3. Quét mã QR hiện lên bằng ứng dụng Expo Go.
4. Vào tab **Settings** trong app và nhập IP máy tính (ví dụ: `http://192.168.1.100:5000`).

**Build & Chạy local (Không qua Expo Cloud):**
Nếu bạn có cài **Android Studio & SDK** trên máy, bạn có thể build và cài trực tiếp vào điện thoại cắm cáp:
```bash
cd mobile
# Tạo thư mục android/ (Prebuild)
npx expo prebuild
# Build và chạy thẳng vào máy (yêu cầu bật USB Debugging)
npx expo run:android
```
*Lưu ý: Cách này sẽ tạo ra folder `android/` trong thư mục `mobile/` và build code native trực tiếp trên máy của bạn.*

---
# auto_service
