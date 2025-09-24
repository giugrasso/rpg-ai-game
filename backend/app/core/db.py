from typing import AsyncGenerator

from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Async engine
engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=True,
    future=True,
)

# Async session factory
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# Dépendance FastAPI
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:  # type: ignore
        yield session
