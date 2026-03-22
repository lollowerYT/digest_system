from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import BaseDAO
from app.database.models.channel import TelegramChannel


class TelegramChannelDAO(BaseDAO):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TelegramChannel)
        
    async def get_by_telegram_id(self, telegram_id: int):
        return await self.get_one_or_none(telegram_id=telegram_id)

    async def get_by_username(self, username: str):
        return await self.get_one_or_none(link=username)
