from pathlib import Path
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from typing import AsyncGenerator, List, Optional
from domain.models import Base
from services.cache import cache


# NOTE: tables created using alembic migrations
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # initialize redis cache:
    await cache.connect()


async def close_db() -> None:
    await engine.dispose()
    # close redis connection:
    await cache.disconnect()


# async db session: 
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# database setup and configuration:
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/shortened_links.db"

# create async engine for database operations:
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

# create async session maker for database sessions:
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)
