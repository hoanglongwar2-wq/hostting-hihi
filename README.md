# PyHost Render Demo (Free)

Giao diện Python Hosting demo nhiều tài khoản. Có đăng ký/đăng nhập, tạo project, upload/tạo/sửa/xóa file, quản lý `requirements.txt`, và chạy thử Python bằng một interpreter giới hạn.

## Quan trọng: giới hạn an toàn của bản Render Free

Bản này **không chạy bot nền thật, không pip install package tùy ý, không hỗ trợ Discord/Telegram bot chạy 24/7**. Để tránh biến web công khai thành dịch vụ thực thi mã tùy ý trên máy chủ Render, nút chạy dùng interpreter demo chỉ hỗ trợ một tập cú pháp nhỏ (`print`, biến, toán tử, `if`, `for range`, `len`, `sum`, ...). Lệnh `import`, truy cập file, network, subprocess, class/function definitions đều bị từ chối.

Render Free có filesystem tạm thời; file và SQLite có thể mất khi service restart/redeploy hoặc instance thay thế. Free web services cũng sleep khi không có traffic. Dùng để demo UI/API, không dùng làm hosting production hoặc lưu dữ liệu quan trọng.

## Deploy bằng GitHub + Render

1. Giải nén ZIP.
2. Tạo repository mới trên GitHub và upload toàn bộ nội dung thư mục (đảm bảo `render.yaml` ở root).
3. Đăng nhập Render: https://render.com
4. Chọn **New + → Blueprint**.
5. Kết nối GitHub repository vừa tạo.
6. Render đọc `render.yaml`; chọn **Apply** để tạo web service.
7. Đợi deploy thành công, mở URL `https://<service>.onrender.com`.
8. Đăng ký tài khoản và tạo project thử nghiệm.

Có thể deploy thủ công bằng Web Service:
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`

## Git commands (nếu upload bằng Git)

```bash
git init
git add .
git commit -m "Initial PyHost Render demo"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin main
```

## Demo Python được hỗ trợ

```python
name = "PyHost"
print("Hello", name)

total = 0
for i in range(5):
    total += i
print("total =", total)

if total == 10:
    print("All good!")
```

## Cấu trúc

- `app/main.py`: FastAPI API + static UI
- `app/auth.py`: JWT auth
- `app/safe_runner.py`: interpreter Python demo giới hạn
- `app/static/`: giao diện
- `render.yaml`: cấu hình Render Blueprint

## Tài khoản và dữ liệu

SQLite và project files nằm trong `/tmp/pyhost-data` trên Render. Không có persistent disk ở Free plan, do đó dữ liệu không được đảm bảo tồn tại. Không upload token bot, mật khẩu, khóa API hay dữ liệu nhạy cảm.

## Chuyển sang hosting chạy bot thật

Cần worker riêng có Docker/container isolation, persistent storage, quota, network policy, quản trị abuse và giám sát. Không nên bật `subprocess` hoặc mount Docker socket vào web service public Render Free.
