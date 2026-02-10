import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Define the connection string (Using aiosqlite for Async)
DATABASE_URL = f"sqlite+aiosqlite:///{settings.DATA_BASE_DIR}/scheduler.db"

# Create the Async Engine
# check_same_thread=False is strictly required for SQLite in async contexts
engine = create_async_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)

# GLOBAL SESSION FACTORY
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)
