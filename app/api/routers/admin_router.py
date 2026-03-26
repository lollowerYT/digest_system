from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.stats import SSystemMetricsResponse, SUserActivityResponse, SUserRegistrationsResponse
from app.api.schemas.user import SUpdateUserTokens, SUserProfile
from app.dao.query_history import QueryHistoryDAO
from app.dao.request_log import RequestLogDAO
from app.dao.user import UserDAO
from app.database.database import get_session
from app.exceptions import NegativeTokensAmountException
from app.services.token_service import TokenService
from app.utils.admin.dependencies import get_admin


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin)]
)


@router.get("/users")
async def get_users(
    session: AsyncSession = Depends(get_session)
) -> list[SUserProfile]:
    user_dao = UserDAO(session)
    users = await user_dao.get_all()
    return [SUserProfile.model_validate(user) for user in users]


@router.patch("/users/{user_id}/tokens")
async def set_user_tokens(
    user_id: UUID,
    data: SUpdateUserTokens,
    session: AsyncSession = Depends(get_session)
):
    user_dao = UserDAO(session)
    user = await user_dao.get_by_id(user_id)
    
    try:
        if data.operation == "MANUAL_ADD":
            await TokenService.add_tokens(session, user, data.amount)
        elif data.operation == "MANUAL_SET":
            await TokenService.set_tokens(session, user, data.amount)
    except ValueError:
        raise NegativeTokensAmountException()
    
    await session.commit()


@router.get("/stats/activity/{date_from}/{date_to}")
async def get_activity_stats(
    date_from: datetime,
    date_to: datetime,
    group_by: Literal["day", "hour"] = "day",
    user_id: Optional[uuid.UUID] = None,
    session: AsyncSession = Depends(get_session)
) -> list[SUserActivityResponse]:
    date_from = date_from.replace(tzinfo=None)
    date_to = date_to.replace(tzinfo=None)
    
    query_history_dao = QueryHistoryDAO(session)
    activity = await query_history_dao.get_activity(
        date_from,
        date_to,
        group_by,
        user_id
    )
    return [SUserActivityResponse.model_validate(a) for a in activity]


@router.get("/stats/registrations/{date_from}/{date_to}")
async def get_registrations_stats(
    date_from: datetime,
    date_to: datetime,
    group_by: Literal["day", "week", "month"] = "day",
    session: AsyncSession = Depends(get_session)
) -> list[SUserRegistrationsResponse]:
    date_from = date_from.replace(tzinfo=None)
    date_to = date_to.replace(tzinfo=None)
    
    user_dao = UserDAO(session)
    registrations = await user_dao.get_user_registrations(
        date_from,
        date_to,
        group_by,
    )
    return [SUserRegistrationsResponse.model_validate(reg) for reg in registrations]


@router.get("/stats/metrics/{date_from}/{date_to}")
async def get_system_metrics(
    date_from: datetime,
    date_to: datetime,
    group_by: Literal["hour", "day"] = "day",
    session: AsyncSession = Depends(get_session)
) -> list[SSystemMetricsResponse]:
    date_from = date_from.replace(tzinfo=None)
    date_to = date_to.replace(tzinfo=None)
    
    request_log_dao = RequestLogDAO(session)
    metrics = await request_log_dao.get_metrics(
        date_from,
        date_to,
        group_by,
    )
    return [SSystemMetricsResponse.model_validate(m) for m in metrics]


from fastapi.responses import FileResponse

@router.get("/dashboard")
async def dashboard():
    return FileResponse("app/static/dashboard.html")
