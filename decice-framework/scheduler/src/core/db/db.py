import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 1. Define the connection string (Using aiosqlite for Async)
DATABASE_URL = f"sqlite+aiosqlite:///{settings.DATA_BASE_DIR}/scheduler.db"

# 2. Create the Async Engine
# check_same_thread=False is strictly required for SQLite in async contexts
engine = create_async_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)

# 3. GLOBAL SESSION FACTORY (This is what the Worker needs!)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# from typing import Optional

# from sqlalchemy.ext.asyncio import AsyncEngine

# engine: Optional[AsyncEngine] = None
