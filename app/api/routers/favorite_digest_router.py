from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.api.schemas.favorite_digest import SFavoriteDigestData
from app.dao.digest import DigestDAO
from app.dao.favorite_digest import FavoriteDigestDAO
from app.database.database import get_session
from app.database.models.user import User
from app.exceptions import DigestAlreadyExistsException, DigestNotExistsException
from app.utils.auth.dependencies import get_current_user
from app.utils.digest_schema_creators import build_favorite_digest_schema


router = APIRouter(prefix="/digests/favorites", tags=["favorites"])


@router.get("/")
async def get_user_favorites(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> list[SFavoriteDigestData]:
    favorite_dao = FavoriteDigestDAO(session)
    digests = await favorite_dao.get_user_favorite_digests(user.id)
    return [SFavoriteDigestData.model_validate(digest) for digest in digests]


@router.post("/new")
async def add_favorite_digest(
    digest_id: UUID | str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> SFavoriteDigestData:
    digest_dao = DigestDAO(session)
    digest = await digest_dao.get_by_id(digest_id)
    if not digest:
        raise DigestNotExistsException()
    
    favorite_dao = FavoriteDigestDAO(session)
    
    existed_favorite = await favorite_dao.get_one_or_none(digest_id=digest_id, user_id=user.id)
    if existed_favorite:
        raise DigestAlreadyExistsException()
    
    new_favorite = await favorite_dao.create(
        user_id=user.id,
        digest_id=digest_id,
    )
    await session.commit()
    return build_favorite_digest_schema(new_favorite, digest)


@router.delete("/{favorite_id}")
async def delete_user_favorite_digest(
    favorite_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> SFavoriteDigestData:
    favorite_dao = FavoriteDigestDAO(session)
    deleted_favorite = await favorite_dao.delete(user_id=user.id, id=favorite_id)
    await session.commit()
    try:
        model = SFavoriteDigestData.model_validate(deleted_favorite)
    except ValidationError as e:
        raise HTTPException(status_code=500)
    return model
