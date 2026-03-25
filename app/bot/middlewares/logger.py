import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import async_sessionmaker

from datetime import datetime
from app.dao.request_log import RequestLogDAO
from app.database.models.request_log import RequestLog
from app.database.database import async_session_maker


class LoggingMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        super().__init__()
        self.session_pool = session_pool
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        update = event if isinstance(event, Update) else data.get("event_update", event)

        start_time = time.perf_counter()

        try:
            result = await handler(event, data)
            status = "success"
        except Exception as e:
            raise
        else:

            duration_ms = (time.perf_counter() - start_time) * 1000

            async with async_session_maker() as session:
                dao = RequestLogDAO(session)
                log_entry = RequestLog(
                    path="telegram_bot",
                    method="update",
                    status_code=200,
                    duration_ms=duration_ms,
                )
                session.add(log_entry)
                await session.commit()

        return result