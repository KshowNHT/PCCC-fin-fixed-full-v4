"""Async SQLAlchemy engine/session setup (PostgreSQL).

Theo kế hoạch Ngày 1: "Khởi tạo FastAPI, kết nối PostgreSQL."
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

# Đảm bảo loại bỏ khoảng trắng dư thừa, xuống dòng (nếu copy paste bị lỗi trên Render)
db_url = DATABASE_URL.strip() if DATABASE_URL else ""

# Tự động thay thế postgres:// hoặc postgresql:// mặc định của Render thành postgresql+asyncpg:// 
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Tách bỏ phần query parameters (như ?sslmode=require) khỏi URL để tránh asyncpg bị lỗi xung đột tham số
db_url = db_url.split("?")[0]

# Lưu ý: Render Internal DB có thể không cần SSL, nhưng External thì bắt buộc. 
# "ssl": "require" an toàn để kết nối tới Render Postgres.
engine = create_async_engine(
    db_url, 
    echo=False, 
    pool_pre_ping=True,
    connect_args={"ssl": "require"}
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Tạo bảng nếu chưa tồn tại. MVP dùng create_all; production nên chuyển
    sang Alembic migrations (xem README mục Next Recommendation)."""
    import app.db_models  # noqa: F401 - đảm bảo models được đăng ký với Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
