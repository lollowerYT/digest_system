from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import BaseDAO
from app.database.models.subscription import Subscription


class SubscriptionDAO(BaseDAO):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Subscription)
