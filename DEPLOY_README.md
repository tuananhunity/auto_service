# Setup Deploy lên Server với GitHub Actions

## Bước 1: Chuẩn bị Server
- Đảm bảo server Linux có Docker và Docker Compose installed.
- Tạo thư mục cho project, ví dụ: `/home/user/auto-service`
- Clone repo hoặc copy files vào thư mục đó.
- Đảm bảo ports 5432, 5500, 6080 available.

## Bước 2: Cấu hình GitHub Secrets
Trong GitHub repo, đi đến Settings > Secrets and variables > Actions, thêm các secrets sau:

- `SERVER_HOST`: IP hoặc domain của server
- `SERVER_USER`: Username SSH (ví dụ: root hoặc ubuntu)
- `SERVER_SSH_KEY`: Private SSH key để connect (tạo bằng `ssh-keygen`, paste private key vào đây)

> **Lưu ý:** Workflow sử dụng GitHub Container Registry (ghcr.io), không cần tài khoản Docker Hub riêng. Images sẽ được push lên `ghcr.io/anhtuan/auto_service/`.

## Bước 3: Cập nhật Workflow
- Trong `.github/workflows/deploy.yml`, thay đổi branch trigger nếu cần.
- Thay đổi đường dẫn trong script SSH: `cd /path/to/your/project` thành đường dẫn thực trên server.

## Bước 4: Cập nhật Docker Compose
- File `web/docker/docker-compose.yml` đã được cấu hình để pull images từ GitHub Container Registry.
- Không cần tạo file `.env` hoặc set biến môi trường.

## Bước 5: Chạy lần đầu
- Push code lên main branch để trigger deploy.
- Sau deploy, SSH vào server và chạy seed admin:
  ```
  docker-compose exec backend python scripts/seed_admin.py
  ```

## Bước 6: Cấu hình Domain và SSL
- Đảm bảo domain point đến server IP.
- Sử dụng Nginx hoặc Caddy để reverse proxy ports 5500 và 6080.
- Cài SSL certificate với Let's Encrypt.

## Lưu ý
- Thay đổi `SECRET_KEY` trong docker-compose.yml thành key bảo mật.
- Đảm bảo firewall mở ports cần thiết.
- Monitor logs với `docker-compose logs`.