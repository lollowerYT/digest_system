# services/telegram_collector.py
import asyncio
from datetime import datetime
from typing import List
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError
from sqlalchemy import select

from app.database.models.channel import TelegramChannel
from app.database.models.news import News
from app.database.database import async_session_maker

class TelegramCollector:
    def __init__(self, api_id: int, api_hash: str, phone: str, session_name: str = 'user_session'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.client = None

    async def _ensure_client(self):
        if self.client is None:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            print("✅ TelegramCollector: клиент подключён")

    async def get_entity(self, link: str):
        await self._ensure_client()
        return await self.client.get_entity(link)

    async def collect_news_for_channels(self, channels: List[TelegramChannel], date_from: datetime) -> List[News]:
        await self._ensure_client()
        new_news = []

        async with async_session_maker() as session:
            for channel in channels:
                if not channel.is_active:
                    continue
                try:
                    entity = await self.client.get_entity(channel.username)  # username = link
                    print(f"📡 Скачиваем сообщения из {channel.username}...")
                    async for msg in self.client.iter_messages(entity, reverse=False):
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
                                new_news.append(news_item)
                    await session.commit()
                except ChannelPrivateError:
                    print(f"❌ Канал {channel.username} закрыт. Помечаем как неактивный.")
                    channel.is_active = False
                    await session.commit()
                except FloodWaitError as e:
                    print(f"⚠️ Ожидание {e.seconds} сек...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"❌ Ошибка при обработке {channel.username}: {e}")

        return new_news

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            