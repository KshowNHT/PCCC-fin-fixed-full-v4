"""Async SQLAlchemy engine/session setup (PostgreSQL).

Theo kế hoạch Ngày 1: "Khởi tạo FastAPI, kết nối PostgreSQL."
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

_options = {"connect_args": {"timeout": 10, "command_timeout": 90}, "pool_timeout": 10, "pool_size": 5, "max_overflow": 5} if DATABASE_URL.startswith("postgresql") else {}
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, **_options)
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

    if os.getenv("PCCC_USE_MIGRATIONS") == "true":
        return  # entrypoint applies versioned migrations before accepting requests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
