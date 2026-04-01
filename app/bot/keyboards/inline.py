import uuid

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData


def main_menu(user_role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="👤 Личный кабинет", callback_data="menu_profile")
    builder.button(text="⭐ Избранное", callback_data="menu_favorites")
    builder.button(text="📰 Сгенерировать дайджест", callback_data="menu_digest")
    builder.button(text="📡 Мои каналы", callback_data="menu_channels")
    if user_role == "ADMIN":
        builder.button(text="⚙️ Админ панель", callback_data="menu_admin")
        builder.adjust(2, 2, 1)
    else:
        builder.adjust(2, 2)

    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Воспользуйтесь меню:")


def profile_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="💰 Поменять тариф", callback_data="subsription_change")
    builder.button(text="📜 История запросов", callback_data="profile_history")
    builder.button(text="⬅️ В меню", callback_data="menu_main")

    builder.adjust(2, 1)

    return builder.as_markup(resize_keyboard=True)


def channels_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="➕ Добавить канал", callback_data="channel_add")
    builder.button(text="➖ Удалить канал", callback_data="channel_remove")
    builder.button(text="⬅️ В меню", callback_data="menu_main")
    builder.adjust(2, 1)

    return builder.as_markup(resize_keyboard=True)


class ToggleChannelCD(CallbackData, prefix="tgl_ch"):
    channel_id: uuid.UUID


def remove_channels(channels: list, selected_ids: list[uuid.UUID]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for channel in channels:
        marker = "🗑 " if channel.id in selected_ids else ""
        text = f"{marker}{channel.name} (@{channel.username})"

        builder.button(
            text=text,
            callback_data=ToggleChannelCD(channel_id=channel.id)
        )

    builder.adjust(1)

    builder.row(
        InlineKeyboardButton(text="❌ Удалить выбранные", callback_data="confirm_delete_channels")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_channels")
    )

    return builder.as_markup()


def digest_menu(selected_formats: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    text_btn = "✅ Текст" if "text" in selected_formats else "Текст"
    audio_btn = "✅ Аудио" if "audio" in selected_formats else "Аудио"

    builder.button(text=text_btn, callback_data="format_text")
    builder.button(text=audio_btn, callback_data="format_audio")
    builder.button(text="➡️ Готово", callback_data="confirm_format")

    builder.adjust(2, 1)

    return builder.as_markup(resize_keyboard=True)


def add_to_favorites(digest_id: uuid.UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="⭐ Добавить в избранное", callback_data=f"add_digest_{digest_id}")
    builder.button(text="⬅️ В меню", callback_data="menu_main")
    builder.adjust(1, 1)

    return builder.as_markup(resize_keyboard=True)


def admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🪙 Поменять кол-во токенов", callback_data="tokens_change")
    builder.button(text="👥 Все пользователи", callback_data="all_users")
    builder.button(text="📊 Посмотреть график регистраций", callback_data="log_in_chart")
    builder.button(text="📊 Посмотреть график активности", callback_data="activity_chart")
    builder.button(text="📊 Посмотреть метрики", callback_data="metrics_chart")
    builder.button(text="⬅️ В меню", callback_data="menu_main")
    builder.adjust(2, 2, 1, 1)

    return builder.as_markup(resize_keyboard=True)

def date_range_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="📅 Последние 7 дней", callback_data="range_7d")
    builder.button(text="📅 Последние 14 дней", callback_data="range_14d")
    builder.button(text="📅 Последний месяц", callback_data="range_month")
    builder.button(text="📆 Ввести вручную", callback_data="range_manual")
    builder.button(text="🔙 Назад", callback_data="menu_admin")

    return builder.as_markup(resize_keyboard=True)


def token_menu(users) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for user in users:
        name = user.first_name or user.username or f"ID {user.telegram_id}"
        text = f"{name} | 🪙 {user.token_balance} токенов"
        builder.button(text=text, callback_data=f"set_tokens_{user.telegram_id}")

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu_admin"))

    return builder.as_markup(resize_keyboard=True)
