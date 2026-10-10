FROM python:3.12-slim

WORKDIR /app

# curl: HEALTHCHECK. poppler-utils: pdf2image (Ngày 12-17 kế hoạch - OCR đọc bản vẽ PDF).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements*.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements-lock.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini entrypoint.sh ./
RUN chmod +x entrypoint.sh
COPY data ./data
COPY data/Roboto-Regular.ttf data/Roboto-Medium.ttf ./fonts/

# SECURITY HARDENING (audit \brutal \10x): trước đây container chạy bằng
# root mặc định — nếu có lỗ hổng RCE trong dependency (Python/thư viện),
# kẻ tấn công có ngay quyền root bên trong container. Tạo user riêng
# không có quyền hệ thống, chown thư mục /app cho user đó, chạy ứng dụng
# bằng user này (defense in depth, không thay thế các lớp vá lỗ hổng khác).
RUN useradd --create-home --shell /usr/sbin/nologin --uid 1001 pccc \
    && chown -R pccc:pccc /app
USER pccc

ENV NODE_ENV=production \
    PORT=3000 \
    PCCC_DATA_DIR=/app/data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["./entrypoint.sh"]
