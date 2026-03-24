from datetime import datetime
from typing import Literal
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import BaseDAO
from app.database.models.request_log import RequestLog


class RequestLogDAO(BaseDAO):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RequestLog)
    
    async def get_metrics(
        self,
        date_from: datetime,
        date_to: datetime,
        group_by: Literal["hour", "day"] = "day",
    ):
        date_trunc = func.date_trunc(group_by, RequestLog.created_at)

        stmt = select(
            date_trunc.label("period"),
            func.count().label("total_requests"),
            func.avg(RequestLog.duration_ms).label("avg_response_time"),
            func.count().filter(RequestLog.status_code >= 500).label("errors")
        ).where(
            RequestLog.created_at.between(date_from, date_to)
        ).group_by("period").order_by("period")

        result = await self.session.execute(stmt)
        return result.all()
