from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.channel import STelegramChannel, SChannelAdd
from app.dao.channel import TelegramChannelDAO
from app.dao.user_channel import UserTelegramChannelDAO
from app.database.database import get_session
from app.database.models.user import User
from app.utils.admin.dependencies import get_admin
from app.utils.auth.dependencies import get_current_user
from app.api.dependencies import get_collector
from app.processing.services.telegram_collector import TelegramCollector

import traceback

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/channels")
async def get_user_channels(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> list[STelegramChannel]:
    user_channel_dao = UserTelegramChannelDAO(session)
    channels = await user_channel_dao.get_user_channels(user.id)
    return [STelegramChannel.model_validate(channel) for channel in channels]


@router.post("/channels")
async def add_user_channel(
    data: SChannelAdd,
    user: User = Depends(get_current_user),
    collector: TelegramCollector = Depends(get_collector),
    session: AsyncSession = Depends(get_session)
):
    # 1. Проверяем существование канала через Telethon
    try:
        entity = await collector.get_entity(data.link)
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=404, detail="Channel not found")

    # 2. Находим или создаём канал в БД
    channel_dao = TelegramChannelDAO(session)
    channel = await channel_dao.get_by_telegram_id(entity.id)
    
    if not channel:
        # Используем метод create из DAO (он уже добавляет в сессию)
        channel = await channel_dao.create(
            telegram_id=entity.id,
            name=entity.title,
            username=data.link,
            is_active=True
        )
        await session.flush()

    # 3. Проверяем, не добавлен ли уже этот канал пользователем
    user_channel_dao = UserTelegramChannelDAO(session)
    user_channels = await user_channel_dao.get_user_channels(user.id)
    
    # Проверяем, есть ли канал в списке
    for uc in user_channels:
        if uc.id == channel.id:
            raise HTTPException(status_code=400, detail="Channel already added")

    # 4. Создаём связь
    await user_channel_dao.create(user_id=user.id, channel_id=channel.id)
    await session.commit()

    return {"status": "ok", "channel": STelegramChannel.model_validate(channel)}


@router.delete("/channels/{channel_id}")
async def delete_user_channel(
    channel_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> STelegramChannel:
    user_channel_dao = UserTelegramChannelDAO(session)
    deleted_channel = await user_channel_dao.delete(user_id=user.id, channel_id=channel_id)
    await session.commit()
    return STelegramChannel.model_validate(deleted_channel)


@router.get("/channels/all", dependencies=[Depends(get_admin)])
async def get_all_channels(
    session: AsyncSession = Depends(get_session)
) -> list[STelegramChannel]:
    channel_dao = TelegramChannelDAO(session)
    channels = await channel_dao.get_all()
    return [STelegramChannel.model_validate(channel) for channel in channels]

