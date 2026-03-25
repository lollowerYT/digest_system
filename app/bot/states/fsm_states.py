from aiogram.fsm.state import State, StatesGroup


class DigestCreation(StatesGroup):
    waiting_for_period = State()
    waiting_for_filter = State()
    waiting_for_clusters = State()
    waiting_for_format = State()


class ChannelManagement(StatesGroup):
    waiting_for_url = State()


class AdminManagement(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_date_period = State()
