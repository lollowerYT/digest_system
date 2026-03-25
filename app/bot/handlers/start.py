from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import main_menu
from app.dao.request_log import RequestLogDAO
from app.database.models import User


router = Router()


@router.message(CommandStart())
async def start(message: Message, user: User):
    await message.answer(
        "<b>Привет! Я твой персональный аналитик новостей.</b> 👋\n\n"
        "Я помогаю экономить время, превращая сотни сообщений из Telegram-каналов в краткие и структурированные дайджесты.\n\n"
        "<i>Воспользуйся меню ниже, чтобы настроить свои источники или создать первый дайджест.</i>",
        reply_markup=main_menu(user.role.value)
    )