import time
from starlette.requests import Request
from app.database.database import async_session_maker
from app.database.models.request_log import RequestLog


async def log_requests_middleware(request: Request, call_next):
    start = time.time()

    response = await call_next(request)

    duration = (time.time() - start) * 1000

    async with async_session_maker() as session:
        log = RequestLog(
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration
        )
        session.add(log)
        await session.commit()

    return response
