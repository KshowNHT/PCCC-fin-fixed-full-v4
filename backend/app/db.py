"""Async SQLAlchemy engine/session setup (PostgreSQL).

Theo kế hoạch Ngày 1: "Khởi tạo FastAPI, kết nối PostgreSQL."
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
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
