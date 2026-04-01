import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import main_menu, profile_menu, add_to_favorites
from app.dao.digest import DigestDAO
from app.dao.cluster import ClusterDAO
from app.dao.query_history import QueryHistoryDAO
from app.dao.subscription import SubscriptionDAO
from app.database.models.user import User
from app.config import settings

router = Router()

@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery, session: AsyncSession, user: User):
    display_name = user.first_name or "Неизвестно"
    role_name = "Администратор" if user.role.value == "ADMIN" else "Пользователь"

    subscription_dao = SubscriptionDAO(session)
    subscription = await subscription_dao.get_one_or_none()
    subscription_name = subscription.name if subscription else "Отсутствует"

    text = (
        "👤 <b>Личный кабинет</b>\n\n"
        f"<b>Имя:</b> {display_name}\n"
        f"<b>Роль:</b> {role_name}\n"
        f"<b>Тариф:</b> {subscription_name}\n"
        f"<b>Доступно токенов:</b> {user.token_balance}\n\n"
        f"<b>Дата регистрации:</b> {user.created_at.strftime('%d.%m.%Y')}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=profile_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "subsription_change")
async def change_subsription(callback: CallbackQuery):
    # TODO: Сделать хендлер для смены тарифа
    await callback.message.answer("Ваш тариф меняется...")
    await callback.answer()

@router.callback_query(F.data == "profile_history")
async def show_history(callback: CallbackQuery, session: AsyncSession, user: User):
    """Показывает список дайджестов пользователя (только заголовки) с кнопками для просмотра."""
    history_dao = QueryHistoryDAO(session)
    digest_dao = DigestDAO(session)

    # Получаем все запросы пользователя
    queries = await history_dao.get_all(user_id=user.id)
    if not queries:
        await callback.answer("История пуста")
        return

    # Собираем уникальные digest_id и загружаем дайджесты
    digest_ids = [query.digest_id for query in queries]
    digests = []
    for d_id in digest_ids:
        digest = await digest_dao.get_by_id(d_id)
        if digest:
            digests.append(digest)

    # Сортируем по дате создания (от новых к старым)
    digests.sort(key=lambda d: d.created_at, reverse=True)

    # Формируем клавиатуру
    keyboard = []
    for digest in digests:
        title = digest.title or "Без названия"
        date_str = digest.created_at.strftime("%d.%m.%Y")
        button_text = f"{title} ({date_str})"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"view_digest_{digest.id}")])

    # Кнопка "Назад" в меню
    keyboard.append([InlineKeyboardButton(text="◀️ В меню", callback_data="menu_main")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.edit_text(
        "📜 <b>Ваши дайджесты</b>\n\nВыберите дайджест для просмотра:",
        reply_markup=markup,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_digest_"))
async def view_digest(callback: CallbackQuery, session: AsyncSession, user: User):
    """Отправляет полный дайджест по выбранному digest_id."""
    digest_id_str = callback.data.split("_")[-1]
    digest_dao = DigestDAO(session)
    cluster_dao = ClusterDAO(session)

    try:
        digest = await digest_dao.get_by_id(digest_id_str)
    except:
        await callback.answer("Дайджест не найден")
        return

    if not digest or digest.user_id != user.id:
        await callback.answer("Дайджест не найден")
        return

    # Получаем кластеры этого дайджеста
    clusters = await cluster_dao.get_all(digest_id=digest.id)
    if not clusters:
        await callback.answer("Дайджест пуст")
        return

    # Отправляем дайджест (аналогично тому, как это делает Celery)
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        # Приветственное сообщение
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="📰 *Ваш дайджест*",
            parse_mode="Markdown"
        )

        # Отправляем каждый кластер отдельным сообщением
        for cluster in clusters:
            if cluster.title and cluster.summary_text:
                message_text = f"📌 *{cluster.title}*\n\n{cluster.summary_text}"
                if len(message_text) > 4096:
                    message_text = message_text[:4000] + "...\n(обрезано)"
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=message_text,
                    parse_mode="Markdown"
                )
                await asyncio.sleep(0.5)

        # Кнопки: добавить в избранное и в меню
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="✅ Дайджест готов. Вы можете сохранить его или вернуться в меню:",
            reply_markup=add_to_favorites(digest.id),
            parse_mode="Markdown"
        )

        # Если есть аудио, отправляем
        if digest.audio_path:
            import os
            if os.path.exists(digest.audio_path):
                with open(digest.audio_path, 'rb') as audio_file:
                    await bot.send_audio(
                        chat_id=callback.message.chat.id,
                        audio=audio_file,
                        caption="🎧 Аудио-версия дайджеста"
                    )
    except Exception as e:
        await callback.answer("Ошибка при отправке дайджеста")
        print(f"Error sending digest: {e}")
    finally:
        await bot.session.close()

    await callback.answer()


@router.callback_query(F.data == "menu_main")
async def show_menu(callback: CallbackQuery, user: User):
    text = (
        "<b>Привет! Я твой персональный аналитик новостей.</b> 👋\n\n"
        "Я помогаю экономить время, превращая сотни сообщений из Telegram-каналов в краткие и структурированные дайджесты.\n\n"
        "<i>Воспользуйся меню ниже, чтобы настроить свои источники или создать первый дайджест.</i>"
    )
    await callback.message.edit_text(text, reply_markup=main_menu(user.role.value), parse_mode="HTML")
    await callback.answer()