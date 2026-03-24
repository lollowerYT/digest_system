import json
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import digest_menu, main_menu, add_to_favorites
from app.bot.keyboards.reply import digest_days, skip_filter, back_button
from app.bot.states.fsm_states import DigestCreation
from app.dao.digest import DigestDAO
from app.dao.favorite_digest import FavoriteDigestDAO
from app.dao.query_history import QueryHistoryDAO
from app.database.models import User
from app.processing.tasks.tasks import generate_digest


router = Router()


@router.callback_query(F.data == "menu_digest")
async def start_digest_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DigestCreation.waiting_for_period)
    await callback.message.answer(
        "За какой период проанализировать новости?\n"
        "<i>Выберите количество дней:</i>",
        reply_markup=digest_days(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(DigestCreation.waiting_for_period)
async def process_period(message: Message, state: FSMContext, user: User):
    if message.text == "Назад":
        await state.clear()
        await message.answer(
            "Действие отменено.",
            reply_markup=ReplyKeyboardRemove()
        )

        await message.answer(
            "<b>Привет! Я твой персональный аналитик новостей.</b> 👋\n\n"
            "Я помогаю экономить время, превращая сотни сообщений из Telegram-каналов в краткие и структурированные дайджесты.\n\n"
            "<i>Воспользуйся меню ниже, чтобы настроить свои источники или создать первый дайджест.</i>",
            reply_markup=main_menu(user.role.value), parse_mode="HTML"
        )
        return

    elif not message.text.isdigit() or not (1 <= int(message.text) <= 7):
        await message.answer("Пожалуйста, введите число от 1 до 7.")
        return

    await state.update_data(period=int(message.text))
    await state.set_state(DigestCreation.waiting_for_filter)
    await message.answer(
        "Введите ключевые слова, имена или события для фильтрации новостей.\n\n"
        "Если хотите получить дайджест по всем новостям, нажмите 'Пропустить'.",
        reply_markup=skip_filter()
    )


@router.message(DigestCreation.waiting_for_filter)
async def process_filter(message: Message, state: FSMContext):
    if message.text == "Назад":
        await state.set_state(DigestCreation.waiting_for_period)
        await message.answer(
            "Действие отменено."
        )
        await message.answer(
            "За какой период проанализировать новости?\n"
            "<i>Выберите количество дней:</i>",
            reply_markup=digest_days(), parse_mode="HTML"
        )
        return

    filter_text = message.text if message.text.lower() not in ["пропустить", "назад"] else None

    await state.update_data(news_filter=filter_text)

    await state.set_state(DigestCreation.waiting_for_clusters)
    await message.answer(
        "На сколько тематических групп разбить новости?\n"
        "Введите число (1 - если нужно просто краткое содержание без групп):",
        reply_markup=back_button()
    )


@router.message(DigestCreation.waiting_for_clusters)
async def process_clusters(message: Message, state: FSMContext):
    if message.text == "Назад":
        await state.set_state(DigestCreation.waiting_for_filter)
        await message.answer(
            "Действие отменено."
        )
        await message.answer(
            "Введите ключевые слова, имена или события для фильтрации новостей.\n\n"
            "Если хотите получить дайджест по всем новостям, нажмите 'Пропустить'.",
            reply_markup=skip_filter()
        )
        return

    if not message.text.isdigit() or int(message.text) < 1:
        await message.answer("Пожалуйста, введите целое число больше 0.")
        return

    await state.update_data(clusters=int(message.text), formats=[])
    await state.set_state(DigestCreation.waiting_for_format)
    await message.answer(
        "Выберите формат готового дайджеста:",
        reply_markup=digest_menu([])
    )


@router.callback_query(DigestCreation.waiting_for_format, F.data.startswith("format_"))
async def toggle_format(callback: CallbackQuery, state: FSMContext):
    format_to_toggle = callback.data.split("_")[-1]

    data = await state.get_data()
    current_formats = data.get("formats", [])

    if format_to_toggle in current_formats:
        current_formats.remove(format_to_toggle)
    else:
        current_formats.append(format_to_toggle)

    await state.update_data(formats=current_formats)
    await callback.message.edit_reply_markup(
        reply_markup=digest_menu(current_formats)
    )

    await callback.answer()


@router.callback_query(DigestCreation.waiting_for_format, F.data == "confirm_format")
async def confirm_format(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    user_data = await state.get_data()
    formats = user_data.get("formats", [])

    if not formats:
        await callback.answer("⚠️ Пожалуйста, выберите хотя бы один формат!", show_alert=True)
        return

    format_names = []
    if "text" in formats: format_names.append("Текст")
    if "audio" in formats: format_names.append("Аудио")
    format_type = " + ".join(format_names)

    today = date.today()
    day_search_for = today - timedelta(days=user_data.get('period'))

    await callback.message.answer(
        "⏳ Начинаю сбор и анализ новостей. Это может занять несколько минут...\n\n"
        f"<b>Параметры:</b>\n"
        f"Период поиска: {day_search_for.strftime('%d.%m.%Y')} – {today.strftime('%d.%m.%Y')}\n"
        f"Фильтр: {user_data.get('news_filter') or 'Нет'}\n"
        f"Кластеров: {user_data.get('clusters')}\n"
        f"Формат: {format_type}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    digest_dao = DigestDAO(session)
    digest = await digest_dao.create(
        user_id=user.id,
        filter_query=f"{user_data.get('news_filter')}",
        date_from=today,
        date_to=day_search_for,
        cluster_count=user_data.get('clusters')
    )
    await session.commit()

    request_data = {
        "date_from": digest.date_from.strftime('%d.%m.%Y'),
        "date_to": digest.date_to.strftime('%d.%m.%Y'),
        "filter_query": digest.filter_query,
        "cluster_count": digest.cluster_count,
        "formats": formats
    }

    task = generate_digest.delay(
            user_id=str(user.id),
            digest_id=str(digest.id),
            request_data=request_data
    )

    await callback.message.answer(
        f"<b>{digest.title}</b>\n\n"
        f"{digest.summary_text}\n"
        f"Период поиска: {digest.date_from.strftime('%d.%m.%Y')} – {digest.date_to.strftime('%d.%m.%Y')}\n"
        f"Дата создания: {digest.created_at.strftime('%d.%m.%Y')}",
        parse_mode="HTML",
        reply_markup=add_to_favorites(digest.id)
    )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("add_digest_"))
async def add_digest_to_favorite(callback: CallbackQuery, session: AsyncSession, user: User):
    digest_id = callback.data.split("_")[-1]

    favorite_dao = FavoriteDigestDAO(session)

    await favorite_dao.create(
        user_id=user.id,
        digest_id=digest_id
    )
    await session.commit()

    await callback.answer("Дайджест успешно добавлен в избранное")

    await callback.message.answer(
        "<b>Привет! Я твой персональный аналитик новостей.</b> 👋\n\n"
        "Я помогаю экономить время, превращая сотни сообщений из Telegram-каналов в краткие и структурированные дайджесты.\n\n"
        "<i>Воспользуйся меню ниже, чтобы настроить свои источники или создать первый дайджест.</i>",
        reply_markup=main_menu(user.role.value), parse_mode="HTML"
    )


