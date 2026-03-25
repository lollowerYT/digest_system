import io
import uuid
from datetime import datetime, date, timedelta
from typing import Literal, Optional
import matplotlib.pyplot as plt

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import admin_menu
from app.bot.keyboards.reply import digest_days, skip_filter, back_button
from app.bot.states.fsm_states import AdminManagement
from app.dao.query_history import QueryHistoryDAO
from app.dao.request_log import RequestLogDAO
from app.dao.user import UserDAO
from app.database.models import User


router = Router()


@router.callback_query(F.data == "menu_admin")
async def show_admin_menu(callback: CallbackQuery):
    await callback.message.answer(
        "Вы вошли в админ-панель.\n"
        "Выберите действие:",
        reply_markup=admin_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "tokens_change")
async def start_change_tokens(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminManagement.waiting_for_user_id)

    await callback.message.answer()
    await callback.answer()


@router.callback_query(F.data == "log_in_chart")
async def start_log_in_chart_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminManagement.waiting_for_date_period)
    await state.update_data(chart_type="log_in", group_by="day")

    await callback.message.answer(
        "Введите период через запятую:\n"
        "<i>Например: 2025-03-01, 2025-03-25</i>\n"
        "<i>или с временем: 2025-03-01 12:30:00, 2025-03-25 23:59:59</i>",
        parse_mode="HTML"
        )
    await callback.answer()



@router.callback_query(F.data == "activity_chart")
async def start_activity_chart_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminManagement.waiting_for_date_period)
    await state.update_data(chart_type="activity", group_by="day")

    await callback.message.answer(
        "Введите период через запятую:\n"
        "<i>Например: 2025-03-01, 2025-03-25</i>\n"
        "<i>или с временем: 2025-03-01 12:30:00, 2025-03-25 23:59:59</i>",
        parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "metrics_chart")
async def start_metrics_chart_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminManagement.waiting_for_date_period)
    await state.update_data(chart_type="metrics", group_by="day")

    await callback.message.answer(
        "Введите период через запятую:\n"
        "<i>Например: 2025-03-01, 2025-03-25</i>\n"
        "<i>или с временем: 2025-03-01 12:30:00, 2025-03-25 23:59:59</i>",
        parse_mode="HTML"
        )
    await callback.answer()

@router.message(AdminManagement.waiting_for_date_period)
async def process_chart_creation(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    chart_type = data.get("chart_type")
    group_by = data.get("group_by")

    try:
        parts = [part.strip() for part in message.text.split(',')]

        if len(parts) != 2:
            raise ValueError
        
        start_str, end_str = parts
        start_date = datetime.fromisoformat(start_str)
        end_date = datetime.fromisoformat(end_str)

        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    except ValueError:
        await message.answer("Неверный формат. Введите даты в формате ГГГГ-ММ-ДД (ЧЧ:ММ:СС) через запятую.")
        return
    
    if chart_type == "log_in":
        chart_image = await build_log_in_chart(start_date, end_date, session)
    elif chart_type == "activity":
        chart_image = await build_activity_chart(start_date, end_date, session)
    elif chart_type == "metrics":
        chart_image = await build_metrics_chart(start_date, end_date, session)
    
    await message.answer_photo(photo=chart_image, caption=f"График {chart_type} за период {start_date} – {end_date}")
    
    await state.clear()


async def build_log_in_chart(
        start_date: datetime,
        end_date: datetime,
        group_by: str,
        session: AsyncSession) -> BufferedInputFile:
    user_dao = UserDAO(session)

    registrations = await user_dao.get_user_registrations(
        date_from=start_date,
        date_to=end_date,
        group_by=group_by
    )
    
    if not registrations:
        raise ValueError("Нет данных за выбранный период")

    x = [reg.period for reg in registrations]
    y = [reg.count for reg in registrations]

    title = f"Новые пользователи\nс {start_date.date()} по {end_date.date()}"
    xlabel = "Период"
    ylabel = "Количество регистраций"

    plt.figure(figsize=(12, 6))
    plt.plot(x, y, marker='o', linestyle='-', color='green', linewidth=2)
    plt.title(title)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()

    return BufferedInputFile(buf.getvalue(), filename="registrations.png")
    


async def build_activity_chart(
        start_date: datetime,
        end_date: datetime,
        group_by: str,
        user_id: uuid.UUID,
        session: AsyncSession) -> BufferedInputFile:
    query_history_dao = QueryHistoryDAO(session)

    activity = await query_history_dao.get_activity(
        date_from=start_date,
        date_to=end_date,
        group_by=group_by,
        user_id=user_id
    )

    if not activity:
        raise ValueError("Нет данных за выбранный период")

    x = [act.period for act in activity]
    y = [act.queries_count for act in activity]

    title = f"Активность пользователей\nс {start_date.date()} по {end_date.date()}"
    xlabel = "Период"
    ylabel = "Количество регистраций"

    plt.figure(figsize=(12, 6))
    plt.plot(x, y, marker='o', linestyle='-', color='blue', linewidth=2)
    plt.title(title)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()

    return BufferedInputFile(buf.getvalue(), filename="activity.png")


async def build_metrics_chart(
        start_date: datetime,
        end_date: datetime,
        group_by: str,
        session: AsyncSession) -> BufferedInputFile:
    request_log_dao = RequestLogDAO(session)

    metrics = await request_log_dao.get_metrics(
        date_from=start_date,
        date_to=end_date,
        group_by=group_by
    )

    if not metrics:
        raise ValueError("Нет данных за выбранный период")

    x = [m.period for m in metrics]
    y = [m.avg_response_time for m in metrics]

    title = f"Среднее время ответа API\nс {start_date.date()} по {end_date.date()}"
    xlabel = "Период"
    ylabel = "Время (мс)"

    plt.figure(figsize=(12, 6))
    plt.plot(x, y, marker='o', linestyle='-', color='red', linewidth=2)
    plt.title(title, fontsize=14)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()

    return BufferedInputFile(buf.getvalue(), filename="metrics.png")