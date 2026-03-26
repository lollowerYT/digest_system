import re

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import channels_menu, remove_channels, ToggleChannelCD
from app.dao.channel import TelegramChannelDAO
from app.bot.states.fsm_states import ChannelManagement
from app.dao.user_channel import UserTelegramChannelDAO
from app.database.models import User

router = Router()


@router.callback_query(F.data == "menu_channels")
async def show_channels(callback: CallbackQuery, session: AsyncSession, user: User):
    user_channel_dao = UserTelegramChannelDAO(session)
    channels = [f"{channel.name} ({channel.username})" for channel in await user_channel_dao.get_user_channels(user_id=user.id)]
    text = "Каналов не найдено." if not channels else "\n".join(channels)
    await callback.message.answer(text, reply_markup=channels_menu())
    await callback.answer()


@router.callback_query(F.data == "channel_add")
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelManagement.waiting_for_url)
    await callback.message.answer(
        "Введите ссылки каналов, которые хотите добавить, <b>через запятую</b>.\n"
        "<i>Например: https‌://t.‌me/username, t.‌me/username, @‌username</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ChannelManagement.waiting_for_url)
async def process_channel_url(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, user: User):
    urls = [url.strip() for url in message.text.split(',')]
    results = []

    channel_dao = TelegramChannelDAO(session)
    user_channel_dao = UserTelegramChannelDAO(session)

    for url in urls:
        match = re.search(r'(?:https?://)?(?:t\.me/|@)([a-zA-Z0-9_]+)', url)
        if not match:
            await message.answer(f" Не удалось распознать ссылку: {url}")
            continue

        username = match.group(1)
        print(username)
        
        try:
            current_channel = await channel_dao.get_one_or_none(username=username)

            if current_channel:
                user_channel_existing = await user_channel_dao.get_one_or_none(user_id=user.id, channel_id=current_channel.id)
                print(f"user_channel_existing: {user_channel_existing}\n"
                      f"user.id: {user.id}\n"
                      f"current_channel.id: {current_channel.id}\n")
                if user_channel_existing:
                    results.append(f"ℹ️ @{username} уже есть в списке")
                    continue
                else:
                    await user_channel_dao.create(
                        channel_id=current_channel.id,
                        user_id=user.id
                    )
                await session.commit()
                results.append(f"✅ {current_channel.name}")
            else:
                chat = await bot.get_chat(f"@{username}")

                new_channel = await channel_dao.create(
                    telegram_id=chat.id,
                    username=username,
                    name=chat.title
                )
                await session.commit()

                await user_channel_dao.create(
                    channel_id=new_channel.id,
                    user_id=user.id
                )
                await session.commit()
                results.append(f"✅ {chat.title}")

        except TelegramBadRequest as e:
            print(e)
            results.append(f"❌ Ошибка с {url}: Канал не найден или нет доступа")
            await session.rollback()

    # Получаем ТОЛЬКО каналы пользователя
    user_channels = await user_channel_dao.get_user_channels(user.id)
    channels_list = [f"{channel.name} ({channel.username})" for channel in user_channels]

    # Формируем ответ
    response = "\n".join(channels_list + results) if results else "\n".join(channels_list)
    await message.answer(response, reply_markup=channels_menu())
    await state.clear()


@router.callback_query(F.data == "channel_remove")
async def remove_channel(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    user_channel_dao = UserTelegramChannelDAO(session)
    channels = await user_channel_dao.get_user_channels(user_id=user.id)

    if not channels:
        await callback.answer("Нет каналов для удаления", show_alert=True)
        return

    # Инициализируем в FSM пустой список для выбранных ID
    await state.update_data(selected_channels=[])

    await callback.message.edit_text(
        "Нажмите на каналы, которые хотите удалить, затем нажмите «Удалить выбранные»:",
        reply_markup=remove_channels(channels, [])
    )
    await callback.answer()


@router.callback_query(ToggleChannelCD.filter())
async def toggle_channel(callback: CallbackQuery, callback_data: ToggleChannelCD, state: FSMContext, session: AsyncSession, user: User):
    data = await state.get_data()
    selected_channels = data.get("selected_channels", [])

    channel_id = callback_data.channel_id

    if channel_id in selected_channels:
        selected_channels.remove(channel_id)
    else:
        selected_channels.append(channel_id)

    await state.update_data(selected_channels=selected_channels)

    user_channel_dao = UserTelegramChannelDAO(session)
    channels = await user_channel_dao.get_user_channels(user_id=user.id)

    try:
        await callback.message.edit_reply_markup(
            reply_markup=remove_channels(channels, selected_channels)
        )
    except TelegramBadRequest as e:
        if "message is not modified" in e.message:
            await callback.answer()
        else:
            raise e

    await callback.answer()


@router.callback_query(F.data == "confirm_delete_channels")
async def confirm_delete_channels(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    data = await state.get_data()
    selected_channels = data.get("selected_channels", [])

    if not selected_channels:
        await callback.answer("Вы не выбрали ни одного канала!", show_alert=True)
        return

    user_channel_dao = UserTelegramChannelDAO(session)

    for ch_id in selected_channels:
        channel = await user_channel_dao.get_one_or_none(user_id=user.id, channel_id=ch_id)

        if channel:
            await user_channel_dao.delete(user_id=user.id, channel_id=ch_id)

    await session.commit()
    await state.clear()

    channels = await user_channel_dao.get_user_channels(user_id=user.id)
    text_channels = [f"{ch.name} (@{ch.username})" for ch in channels]
    text = (
            "✅ Выбранные каналы успешно удалены.\n\n"
            "<b>Текущий список:</b>\n" +
            ("\n".join(text_channels) if text_channels else "Каналов не осталось.")
    )

    await callback.message.edit_text(text, reply_markup=channels_menu(), parse_mode="HTML")
    await callback.answer("Удаление завершено!")
