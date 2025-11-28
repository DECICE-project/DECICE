from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from watmon_service.db.models import Base
from typing import AsyncIterator
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.dialects.sqlite.aiosqlite import AsyncAdapt_aiosqlite_connection
from sqlalchemy.pool.base import _ConnectionRecord


DATABASE_URL = "sqlite+aiosqlite:///./data/database.db"
engine = create_async_engine(
    DATABASE_URL,
)
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Set foreign key constraint for sqlite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(
    dbapi_connection: AsyncAdapt_aiosqlite_connection,
    connection_record: _ConnectionRecord,
):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_generate() -> AsyncIterator[AsyncSession]:
    session = async_session_maker()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
