import asyncio
from datetime import datetime
from typing import List
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError
from telethon.sessions import StringSession
from sqlalchemy import select
import redis.asyncio as redis

from app.database.models.channel import TelegramChannel
from app.database.models.news import News
from app.database.database import async_session_maker
from app.config import settings

class TelegramCollector:
    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = None
        self.redis_client = None

    async def _get_redis(self):
        if self.redis_client is None:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True
            )
        return self.redis_client

    async def _ensure_client(self):
        if self.client is None:
            redis_client = await self._get_redis()
            session_key = "telegram_session_string"
            session_string = await redis_client.get(session_key)

            if session_string:
                self.client = TelegramClient(
                    StringSession(session_string),
                    self.api_id,
                    self.api_hash,
                    connection_retries=10,
                    retry_delay=10,
                    request_retries=10,
                    timeout=120,
                    flood_sleep_threshold=60,
                    auto_reconnect=True
                )
            else:
                self.client = TelegramClient(
                    StringSession(),
                    self.api_id,
                    self.api_hash,
                    connection_retries=10,
                    retry_delay=10,
                    request_retries=10,
                    timeout=120,
                    flood_sleep_threshold=60,
                    auto_reconnect=True
                )

            await self.client.start(phone=self.phone)

            if not session_string:
                new_session_string = self.client.session.save()
                await redis_client.set(session_key, new_session_string)
                print("✅ Сессия сохранена в Redis")

            print("✅ TelegramCollector: клиент подключён")

    async def get_entity(self, link: str):
        await self._ensure_client()
        return await self.client.get_entity(link)

    async def collect_news_for_channels(self, channels: List[TelegramChannel], date_from: datetime) -> List[News]:
        await self._ensure_client()
        newly_saved = []  # только для отладочного вывода

        async with async_session_maker() as session:
            for idx, channel in enumerate(channels):
                if not channel.is_active:
                    continue
                try:
                    entity = await self.client.get_entity(channel.username)
                    print(f"📡 Скачиваем сообщения из {channel.username}...")
                    async for msg in self.client.iter_messages(entity, reverse=False, limit=500):
                        if msg.date.replace(tzinfo=None) < date_from:
                            break
                        if msg.text:
                            stmt = select(News).where(News.telegram_message_id == msg.id)
                            existing = await session.execute(stmt)
                            if not existing.scalar_one_or_none():
                                news_item = News(
                                    channel_id=channel.id,
                                    telegram_message_id=msg.id,
                                    text=msg.text,
                                    published_at=msg.date.replace(tzinfo=None)
                                )
                                session.add(news_item)
                                newly_saved.append(news_item)
                        await asyncio.sleep(0.05)
                    await session.commit()
                    print(f"Канал {channel.username}: загружено {len([n for n in newly_saved if n.channel_id == channel.id])} новых сообщений")
                    if idx < len(channels) - 1:
                        await asyncio.sleep(2)
                except ChannelPrivateError:
                    print(f"❌ Канал {channel.username} закрыт. Помечаем как неактивный.")
                    channel.is_active = False
                    await session.commit()
                except FloodWaitError as e:
                    print(f"⚠️ Ожидание {e.seconds} сек...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"❌ Ошибка при обработке {channel.username}: {e}")

        # Получаем все новости за период из БД
        all_news = []
        async with async_session_maker() as session:
            for channel in channels:
                stmt = select(News).where(
                    News.channel_id == channel.id,
                    News.published_at >= date_from
                )
                result = await session.execute(stmt)
                all_news.extend(result.scalars().all())
        print(f"Всего загружено новых новостей: {len(newly_saved)}, всего в БД за период: {len(all_news)}")
        return all_news

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()