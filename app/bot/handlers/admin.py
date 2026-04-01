import io
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from app.bot.keyboards.inline import admin_menu, date_range_keyboard, token_menu
from app.bot.states.fsm_states import AdminManagement
from app.dao.query_history import QueryHistoryDAO
from app.dao.request_log import RequestLogDAO
from app.dao.user import UserDAO

router = Router()


@router.callback_query(F.data == "menu_admin")
async def show_admin_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Вы вошли в админ-панель.\nВыберите действие:",
        reply_markup=admin_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "all_users")
async def show_all_users(callback: CallbackQuery, session: AsyncSession):
    user_dao = UserDAO(session)
    users = await user_dao.get_all()
    if not users:
        await callback.message.answer("Пользователи не найдены.")
        await callback.answer()
        return

    text = "📋 <b>Список пользователей</b>\n\n"
    for user in users:
        name = user.first_name or user.username or "Без имени"
        text += f"🆔 {user.telegram_id} | {name} | 💰 {user.token_balance} токенов\n"

    if len(text) > 4096:
        parts = [text[i:i+4096] for i in range(0, len(text), 4096)]
        for part in parts:
            await callback.message.answer(part, parse_mode="HTML")
    else:
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "tokens_change")
async def show_users_for_token_change(callback: CallbackQuery, session: AsyncSession):
    user_dao = UserDAO(session)
    users = await user_dao.get_all()
    if not users:
        await callback.message.answer("Пользователи не найдены.")
        await callback.answer()
        return

    await callback.message.edit_text("Выберите пользователя для изменения токенов:", reply_markup=token_menu(users))
    await callback.answer()

@router.callback_query(F.data.startswith("set_tokens_"))
async def start_set_tokens(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(user_id=user_id)
    await state.set_state(AdminManagement.waiting_for_tokens_amount)
    await callback.message.edit_text("Введите новое количество токенов (0-999):")
    await callback.answer()

@router.message(AdminManagement.waiting_for_tokens_amount)
async def process_tokens_amount(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    user_id = data.get("user_id")
    tokens_amount = message.text

    if not tokens_amount.isdigit():
        await message.answer("Неправильно набрано количество токенов!")
        return
    tokens_int = int(tokens_amount)
    if tokens_int < 0 or tokens_int > 999:
        await message.answer("Количество токенов должно быть от 0 до 999.")
        return

    user_dao = UserDAO(session)
    user = await user_dao.get_by_telegram_id(user_id)
    if not user:
        await message.answer("Пользователь не найден.")
        await state.clear()
        return

    user.token_balance = tokens_int
    await session.commit()
    await message.answer(f"Баланс пользователя {user.first_name or user.username or f'ID {user.telegram_id}'} установлен на {tokens_int} токенов.")
    await state.clear()
    # Возвращаем в админ-меню
    await message.answer("Выберите действие:", reply_markup=admin_menu())

# ----------------------------------------------------------------------
# Графики (общий поток)
# ----------------------------------------------------------------------
@router.callback_query(F.data.in_(["log_in_chart", "activity_chart", "metrics_chart"]))
async def start_chart_creation(callback: CallbackQuery, state: FSMContext):
    chart_type = callback.data.replace("_chart", "")
    await state.update_data(chart_type=chart_type, group_by="day" if chart_type != "metrics" else "hour")
    await callback.message.edit_text(
        f"Выберите период для графика «{chart_type}»:",
        reply_markup=date_range_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("range_"))
async def handle_range(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    range_type = callback.data.split("_")[1]  # 7d, 14d, month, manual
    now = datetime.now()
    end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    if range_type == "7d":
        start_date = now - timedelta(days=7)
    elif range_type == "14d":
        start_date = now - timedelta(days=14)
    elif range_type == "month":
        start_date = now - timedelta(days=30)
    elif range_type == "manual":
        await state.update_data(chart_start_pending=True)
        await callback.message.edit_text("Выберите дату начала:", reply_markup=await SimpleCalendar().start_calendar())
        await callback.answer()
        return
    else:
        await callback.answer("Неизвестный диапазон")
        return

    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    await generate_and_send_chart(callback.message, state, session, start_date, end_date)
    await callback.answer()

@router.callback_query(SimpleCalendarCallback.filter())
async def process_calendar_selection(
    callback: CallbackQuery,
    callback_data: SimpleCalendarCallback,
    state: FSMContext,
    session: AsyncSession,
):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        data = await state.get_data()
        if data.get("chart_start_pending"):
            await state.update_data(start_date=date, chart_start_pending=False, chart_end_pending=True)
            await callback.message.edit_text("Теперь выберите дату окончания:", reply_markup=await SimpleCalendar().start_calendar())
        elif data.get("chart_end_pending"):
            start_date = data.get("start_date")
            end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            chart_type = data.get("chart_type")
            group_by = data.get("group_by")
            try:
                if chart_type == "log_in":
                    chart_image = await build_log_in_chart(start_date, end_date, group_by, session)
                elif chart_type == "activity":
                    chart_image = await build_activity_chart(start_date, end_date, group_by, session)
                elif chart_type == "metrics":
                    chart_image = await build_metrics_chart(start_date, end_date, group_by, session)
                else:
                    raise ValueError("Неизвестный тип графика")
            except ValueError as e:
                await callback.message.answer(str(e))
                await state.clear()
                return

            caption = f"График {chart_type}\nс {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"
            await callback.message.answer_photo(photo=chart_image, caption=caption)
            await state.clear()
            await callback.message.answer("Выберите действие:", reply_markup=admin_menu())
        else:
            await callback.answer()
    else:
        await callback.answer()


async def generate_and_send_chart(message: Message, state: FSMContext, session: AsyncSession, start_date: datetime, end_date: datetime):
    data = await state.get_data()
    chart_type = data.get("chart_type")
    group_by = data.get("group_by")
    try:
        if chart_type == "log_in":
            chart_image = await build_log_in_chart(start_date, end_date, group_by, session)
        elif chart_type == "activity":
            chart_image = await build_activity_chart(start_date, end_date, group_by, session)
        elif chart_type == "metrics":
            chart_image = await build_metrics_chart(start_date, end_date, group_by, session)
        else:
            raise ValueError("Неизвестный тип графика")
    except ValueError as e:
        await message.answer(str(e))
        return

    caption = f"График {chart_type}\nс {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"
    await message.answer_photo(photo=chart_image, caption=caption)
    await state.clear()
    await message.answer("Выберите действие:", reply_markup=admin_menu())


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
    y = [reg.value for reg in registrations]

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
        session: AsyncSession) -> BufferedInputFile:
    query_history_dao = QueryHistoryDAO(session)
    activity = await query_history_dao.get_activity(
        date_from=start_date,
        date_to=end_date,
        group_by=group_by,
        user_id=None
    )
    if not activity:
        raise ValueError("Нет данных за выбранный период")

    x = [act.period for act in activity]
    y = [act.value for act in activity]

    title = f"Активность пользователей\nс {start_date.date()} по {end_date.date()}"
    xlabel = "Период"
    ylabel = "Количество запросов"

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