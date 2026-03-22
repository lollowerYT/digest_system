import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.cluster import SCluster
from app.api.schemas.digest import SDigest, SDigestCreate
from app.dao.cluster import ClusterDAO
from app.dao.digest import DigestDAO
from app.database.database import get_session
from app.database.models.digest import Digest
from app.database.models.user import User
from app.utils.auth.dependencies import get_current_user
from app.processing.tasks.tasks import generate_digest


router = APIRouter(prefix="/digests", tags=["digests"])


@router.post("/")
async def add_digest(
    data: SDigestCreate,   # схему нужно создать
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if user.token_balance <= 0:
        raise HTTPException(status_code=402, detail="Insufficient tokens")

    digest = Digest(
        user_id=user.id,
        date_from=data.date_from,
        date_to=data.date_to,
        filter_query=data.filter_query,
        cluster_count=data.n_clusters,
        summary_text=None,
        audio_path=None
    )
    session.add(digest)
    await session.commit()
    await session.refresh(digest)

    task = generate_digest.delay(
        user_id=str(user.id),
        digest_id=str(digest.id),
        request_data=data.model_dump()
    )

    return {"digest_id": digest.id, "task_id": task.id}


@router.get("/")
async def get_digest_list():
    pass


@router.get("/{digest_id}")
async def get_digest_by_id(
    digest_id: uuid.UUID | str,
    session: AsyncSession = Depends(get_session)
) -> SDigest:
    digest_dao = DigestDAO(session)
    digest = await digest_dao.get_by_id(digest_id)
    return SDigest.model_validate(digest)


@router.get("/{digest_id}/audio")
async def get_digest_audio(
    digest_id: uuid.UUID | str,
    session: AsyncSession = Depends(get_session)
):
    digest_dao = DigestDAO(session)
    digest = await digest_dao.get_by_id(digest_id)
    audio_path = digest.audio_path
    #  TODO: доделать после добавления ML сервиса


@router.get("/{digest_id}/clusters")
async def get_clusters(
    digest_id: uuid.UUID | str,
    session: AsyncSession = Depends(get_session)
) -> list[SCluster]:
    cluster_dao = ClusterDAO(session)
    clusters = await cluster_dao.get_all(digest_id=digest_id)
    return [SCluster.model_validate(cluster) for cluster in clusters]
