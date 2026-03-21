from app.processing.services.telegram_collector import TelegramCollector
from app.config import settings

_collector = None

async def get_collector():
    global _collector
    if _collector is None:
        _collector = TelegramCollector(
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            phone=settings.PHONE_NUMBER
        )
    return _collector