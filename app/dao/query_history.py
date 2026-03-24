from datetime import datetime
from typing import Literal, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import BaseDAO
from app.database.models.query_history import QueryHistory


class QueryHistoryDAO(BaseDAO):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, QueryHistory)
    
    async def get_activity(
        self,
        date_from: datetime,
        date_to: datetime,
        group_by: Literal["day", "hour"] = "day",
        user_id: Optional[uuid.UUID] = None,
    ):
        date_trunc = func.date_trunc(group_by, QueryHistory.created_at)

        stmt = select(
            date_trunc.label("period"),
            QueryHistory.user_id,
            func.count().label("requests_count")
        ).where(
            QueryHistory.created_at.between(date_from, date_to)
        )
        
        if user_id:
            stmt = stmt.where(QueryHistory.user_id == user_id)
        
        stmt = stmt.group_by("period", QueryHistory.user_id).order_by("period")

        result = await self.session.execute(stmt)
        
        return result.all()
