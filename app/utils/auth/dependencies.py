from fastapi import Depends, Request
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dao.user import UserDAO
from app.database.database import get_session
from app.exceptions import (
    AuthorizationExpiredException,
    InvalidTokenException,
    UserNotAuthenticatedException,
    UserNotFoundException
)
from app.utils.time_utils import utc_now


from fastapi import Request

from fastapi import Request

def get_token(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise UserNotAuthenticatedException()

    return token


async def get_current_user(
    token: str = Depends(get_token),
    session: AsyncSession = Depends(get_session)
):

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise InvalidTokenException()

    expire = payload.get("exp")
    
    if not expire or (int(expire) < utc_now().timestamp()):
        raise AuthorizationExpiredException()
    
    user_id = payload.get("sub")
    
    if not user_id:
        raise UserNotFoundException()

    user_dao = UserDAO(session)
    user = await user_dao.get_by_id(user_id)

    if not user:
        raise UserNotFoundException()

    return user
