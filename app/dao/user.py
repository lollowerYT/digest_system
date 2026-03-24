from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import BaseDAO
from app.database.models.user import User


class UserDAO(BaseDAO):
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)
    
    async def get_by_telegram_id(self, telegram_id: int | str):
        telegram_id = int(telegram_id)
        return await self.get_one_or_none(telegram_id=telegram_id)
