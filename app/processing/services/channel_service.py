# services/channel_service.py
import uuid
from sqlalchemy import select
from app.database.models.channel import TelegramChannel
from app.database.database import async_session_maker
from services.telegram_collector import TelegramCollector

class ChannelService:
    def __init__(self, collector: TelegramCollector):
        self.collector = collector

    async def add_channel(self, link: str) -> TelegramChannel:
        entity = await self.collector.get_entity(link)
        if not entity:
            raise ValueError("Канал не найден")

        async with async_session_maker() as session:
            stmt = select(TelegramChannel).where(TelegramChannel.telegram_id == entity.id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()
            if channel:
                channel.name = entity.title
                channel.link = link
                channel.is_active = True
            else:
                channel = TelegramChannel(
                    telegram_id=entity.id,
                    name=entity.title,
                    link=link,
                    is_active=True
                )
                session.add(channel)
            await session.commit()
            await session.refresh(channel)
            return channel

    async def deactivate_channel(self, channel_id: uuid.UUID):
        async with async_session_maker() as session:
            channel = await session.get(TelegramChannel, channel_id)
            if channel:
                channel.is_active = False
                await session.commit()