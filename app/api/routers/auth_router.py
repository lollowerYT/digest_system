from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import STelegramAuthData
from app.dao.subscription import SubscriptionDAO
from app.dao.user import UserDAO
from app.database.database import get_session
from app.config import settings
from app.exceptions import AuthorizationExpiredException, InvalidTelegramAuthorizationException
from app.utils.auth.jwt import create_access_token
from app.utils.auth.telegram_auth import validate_auth_date, verify_telegram_auth

router = APIRouter(prefix="/auth", tags=["auth"])

from fastapi import Request
    
@router.options("/telegram")
async def options():
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "https://nonthermally-prepossessing-rikki.ngrok-free.dev",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Credentials": "true"
    })

@router.post("/telegram")
async def telegram_login(
    data: STelegramAuthData,
    response: Response,
    session: AsyncSession = Depends(get_session)
):
    payload = data.model_dump()

    print("Token used:", settings.WIDGET_BOT_TOKEN_ACTUAL)
    print("Hash from Telegram:", payload.get('hash'))
    print("All payload keys:", payload.keys())
    print("All payload values:", payload)
    print("Raw data before model_dump:", data)

    # if not verify_telegram_auth(payload, settings.WIDGET_BOT_TOKEN_ACTUAL):
    #     raise InvalidTelegramAuthorizationException()

    if not validate_auth_date(int(payload["auth_date"])):
        raise AuthorizationExpiredException()
        
    
    telegram_id = int(payload["id"])
    
    user_dao = UserDAO(session=session)
    user = await user_dao.get_by_telegram_id(telegram_id)
    # Получаем Base тариф, чтобы установить его для пользователя
    subscription_dao = SubscriptionDAO(session)
    base_subscription = await subscription_dao.get_one_or_none(name="Base")

    if not user:
        user = await user_dao.create(
            telegram_id=telegram_id,
            username=payload.get("username"),
            first_name=payload.get("first_name"),
            subscription_id=base_subscription.id if base_subscription else None
        )
        await session.commit()
        await session.refresh(user)

    access_token = create_access_token(user.id)
    response.headers.append(
        "Set-Cookie",
        f"access_token={access_token}; HttpOnly; Secure; SameSite=None; Partitioned"
    )
    return {
    "access_token": access_token,
    "token_type": "bearer"
    }