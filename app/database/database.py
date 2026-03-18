from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


DATABASE_URL = settings.DATABASE_URL

# Асинхронный движок для обработки запросов 
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

# Создатель сессий
async_session_maker = async_sessionmaker(
    engine=engine,
    expire_on_commit=False,
)

# Эту созданную сессию дальше будем прокидывать как зависимость
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Базовый класс для всех моделей
class Base(DeclarativeBase):
    pass
