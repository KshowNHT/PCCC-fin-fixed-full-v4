"""Khởi tạo dữ liệu mặc định khi database còn trống.

- Admin mặc định (đăng nhập lần đầu, giữ tương thích placeholder admin/admin
  của Login.tsx cũ, nhưng mật khẩu mạnh hơn — xem PCCC_ADMIN_PASSWORD).
- 18 tài liệu pháp lý mặc định (từ default_documents.py, đồng nhất với bản
  JSON-file trước đây, giờ ghi thẳng vào bảng documents).
"""
import logging

from sqlalchemy import func, select

from app.auth import hash_password
from app.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.db import AsyncSessionLocal
from app.db_models import Document, User
from app.default_documents import DEFAULT_DOCUMENTS

logger = logging.getLogger("pccc.seed")


async def seed_initial_data() -> None:
    async with AsyncSessionLocal() as db:
        user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        if user_count == 0:
            admin = User(
                username=DEFAULT_ADMIN_USERNAME,
                full_name="Quản trị viên hệ thống",
                hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            # SECURITY FIX (rà soát "sẵn sàng chạy online" lần 4): trước đây
            # log dòng này IN LUÔN MẬT KHẨU ra log ứng dụng (%s thứ 2 =
            # DEFAULT_ADMIN_PASSWORD) — log container thường được nhiều hệ
            # thống/nhiều người truy cập hơn cả file .env (log aggregation,
            # `docker compose logs`, cloud provider log viewer...). Người vận
            # hành đã tự đặt mật khẩu này trong .env của họ — không cần in
            # lại, chỉ xác nhận đã tạo xong tài khoản.
            logger.info(
                "[Seed] Đã tạo tài khoản admin mặc định: %s (dùng mật khẩu đã đặt trong PCCC_ADMIN_PASSWORD ở .env). "
                "Đổi mật khẩu ngay sau lần đăng nhập đầu qua PUT /api/auth/me/password.",
                DEFAULT_ADMIN_USERNAME,
            )

        doc_count = (await db.execute(select(func.count()).select_from(Document))).scalar_one()
        if doc_count == 0:
            for d in DEFAULT_DOCUMENTS:
                db.add(
                    Document(
                        id=d["id"],
                        code=d["code"],
                        title=d["title"],
                        type=d["type"],
                        link=d["link"],
                        content=d["content"],
                        is_custom=False,
                    )
                )
            logger.info("[Seed] Đã nạp %d tài liệu pháp lý mặc định vào PostgreSQL.", len(DEFAULT_DOCUMENTS))

        await db.commit()
