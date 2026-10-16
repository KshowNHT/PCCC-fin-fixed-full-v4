"""Async SQLAlchemy engine/session setup (PostgreSQL).

Theo kế hoạch Ngày 1: "Khởi tạo FastAPI, kết nối PostgreSQL."
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.config import DATABASE_URL


def _build_engine_options(raw_url: str):
    """Xử lý DATABASE_URL và cấu hình SSL thích ứng cho asyncpg.
    - Loại bỏ query parameter 'sslmode' / 'ssl' mà asyncpg không hỗ trợ trực tiếp từ URL query.
    - Tự động cấu hình SSL Context thích hợp cho cơ sở dữ liệu cloud (Aiven, Render, Neon, Supabase,...)
      trong khi vẫn cho phép kết nối không mã hóa với localhost / Docker nội bộ.
    """
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    if not parsed.scheme.startswith("postgresql"):
        return url, {}

    query_params = parse_qs(parsed.query)
    sslmode = query_params.pop("sslmode", [None])[0]
    ssl_param = query_params.pop("ssl", [None])[0]

    new_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))

    host = parsed.hostname or ""
    is_local = host in ("localhost", "127.0.0.1", "postgres", "db")
    force_ssl = sslmode in ("require", "verify-ca", "verify-full") or ssl_param in ("true", "1", "require")
    disable_ssl = sslmode == "disable" or ssl_param in ("false", "0", "disable")

    connect_args: dict = {"timeout": 10, "command_timeout": 90}

    if (not is_local and not disable_ssl) or force_ssl:
        ctx = ssl.create_default_context()
        ca_file = os.environ.get("PCCC_DB_CA_FILE") or os.environ.get("PGSSLROOTCERT")
        if ca_file and os.path.exists(ca_file):
            ctx.load_verify_locations(ca_file)
        else:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    else:
        connect_args["ssl"] = False

    options = {
        "connect_args": connect_args,
        "pool_timeout": 10,
        "pool_size": 5,
        "max_overflow": 5,
    }
    return clean_url, options


CLEAN_DATABASE_URL, _options = _build_engine_options(DATABASE_URL)
engine = create_async_engine(CLEAN_DATABASE_URL, echo=False, pool_pre_ping=True, **_options)
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
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)