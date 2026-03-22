from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.user import SUpdateUserTokens
from app.dao.user import UserDAO
from app.database.database import get_session
from app.utils.admin.dependencies import get_admin


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin)])


@router.get("/users")
async def get_users():
    pass


@router.patch("/users/{user_id}/tokens")
async def set_user_tokens(
    user_id: UUID,
    data: SUpdateUserTokens,
    session: AsyncSession = Depends(get_session)
):
    user_dao = UserDAO(session)
    


@router.get("/stats/activity")
async def get_activity_stats():
    pass


@router.get("/stats/requests")
async def get_requests_stats():
    pass


@router.get("/stats/registrations")
async def get_registrations_stats():
    pass
