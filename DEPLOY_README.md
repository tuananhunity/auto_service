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
- `SERVER_SSH_KEY`: Private SSH key thô nhiều dòng để connect (tạo bằng `ssh-keygen`, paste trực tiếp toàn bộ nội dung key vào đây, bắt đầu bằng `-----BEGIN ... PRIVATE KEY-----`)

> **Lưu ý:** Workflow sử dụng GitHub Container Registry (ghcr.io), không cần tài khoản Docker Hub riêng. Image sẽ được push theo đúng repo hiện tại dưới dạng `ghcr.io/<owner>/<repo>/auto-service:latest`.
>
> Không base64 encode `SERVER_SSH_KEY` trước khi lưu vào GitHub Secrets. Workflow truyền raw private key trực tiếp vào SSH action.

## Bước 3: Cập nhật Workflow
- Trong `.github/workflows/deploy.yml`, thay đổi branch trigger nếu cần.
- Thay đổi đường dẫn trong script SSH: `cd /path/to/your/project` thành đường dẫn thực trên server.
- Server cần có sẵn repo git tại đường dẫn deploy và có quyền `git fetch/pull` từ remote `origin`.

## Bước 4: Cập nhật Docker Compose
- File `web/docker/docker-compose.yml` dùng chung một image cho cả `backend` và `novnc` thông qua biến `AUTO_SERVICE_IMAGE`.
- Trong GitHub Actions deploy, biến này được set tự động thành `ghcr.io/<owner>/<repo>/auto-service:latest`, nên không cần hardcode namespace registry trong compose file.
- Nếu chạy `docker compose` thủ công ngoài workflow, cần export `AUTO_SERVICE_IMAGE` trước khi start.

## Bước 5: Chạy lần đầu
- Push code lên main branch để trigger deploy.
- Workflow sẽ tự `git fetch`, `git checkout`, và `git pull --ff-only` đúng branch đang deploy trước khi chạy Docker Compose.
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
- Nếu `docker pull` trên server báo `unauthorized`, hãy chạy `docker login ghcr.io` trên server bằng tài khoản/PAT có quyền pull image private.
- Monitor logs với `docker-compose logs`.
