from aiogram.fsm.state import StatesGroup, State

class MessageStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_title = State()
    waiting_for_message = State()
    waiting_for_confirmation = State()