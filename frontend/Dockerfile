# Build React/Vite.
FROM node:20-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Vite variables are embedded at BUILD time, not container runtime.
# FIX (phát hiện khi rà soát QA lần 2): code thực tế đọc
# import.meta.env.VITE_API_BASE_URL (xem src/lib/api.ts, src/components/
# Sidebar.tsx), nhưng biến build-arg trước đây tên là VITE_API_URL — SAI
# TÊN, khiến giá trị truyền vào lúc build không bao giờ có tác dụng (Vite
# chỉ nhúng đúng biến có tiền tố VITE_ VÀ đúng tên được code gọi tới).
#
# FIX NGHIÊM TRỌNG (rà soát "sẵn sàng chạy online" lần 4): giá trị mặc định
# TRƯỚC ĐÂY là "http://localhost:8000" — bị "đóng cứng" (hardcode) vào file
# JS đã build (đã verify bằng cách build thử và grep thấy chuỗi này trong
# bundle). Khi deploy lên domain thật, trình duyệt của MỌI người dùng khác
# sẽ cố gọi API tới "localhost:8000" của CHÍNH MÁY HỌ (không tồn tại) thay
# vì server thật — toàn bộ ứng dụng sẽ không hoạt động ngoài máy Docker
# Desktop cá nhân của người build. Đổi mặc định thành CHUỖI RỖNG (đường dẫn
# tương đối "/api/..."): nhờ vậy dù SPA được mở từ domain/IP/port nào, các
# lệnh gọi API đều tự động trỏ về ĐÚNG origin đang phục vụ trang, được Nginx
# (xem nginx.conf) proxy sang backend nội bộ — hoạt động đúng trên MỌI môi
# trường (localhost, IP VPS, domain thật) mà không cần build lại image theo
# từng nơi deploy. Vẫn có thể override bằng biến môi trường nếu thật sự cần
# trỏ sang 1 domain backend khác hẳn (kiến trúc tách domain).
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# Serve the production build using Nginx.
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
