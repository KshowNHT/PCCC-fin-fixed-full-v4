import asyncio
from sqlalchemy import inspect, text
from alembic import context
from app.db import engine, Base
import app.db_models
from app.config import assert_production_secrets_are_safe
assert_production_secrets_are_safe()

def migrate(connection):
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(72190002)"))
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
        inspector = inspect(connection)
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                raise RuntimeError(f"Missing database table: {table.name}")
            actual = {column["name"] for column in inspector.get_columns(table.name)}
            missing = set(table.columns.keys()) - actual
            if missing:
                raise RuntimeError(f"Database schema mismatch: {table.name}; missing columns: {', '.join(sorted(missing))}")

async def online():
    async with engine.begin() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()

if context.is_offline_mode():
    raise RuntimeError("Use online migrations with configured DATABASE_URL")
else:
    asyncio.run(online())
