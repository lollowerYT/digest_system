from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import BaseDAO
from app.database.models.digest import Digest
from app.database.models.favorite_digest import FavoriteDigest


class FavoriteDigestDAO(BaseDAO):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FavoriteDigest)

    async def get_user_favorite_digests(self, user_id: UUID | str):
        stmt = (
            select(
                FavoriteDigest.id.label("id"),
                FavoriteDigest.digest_id,
                FavoriteDigest.user_id,

                Digest.title,
                Digest.summary_text,
                Digest.filter_query,
                Digest.date_from,
                Digest.date_to,
                Digest.cluster_count,
                Digest.audio_path,
                Digest.created_at,
            )
            .join(FavoriteDigest, FavoriteDigest.digest_id == Digest.id)
            .where(FavoriteDigest.user_id == user_id)
        )
        
        result = await self.session.execute(stmt)
        return result.mappings().all()
