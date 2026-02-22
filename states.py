from aiogram.fsm.state import State, StatesGroup


class UserDataForm(StatesGroup):
    """
    Группа состояний для сбора данных о пользователе.
    Каждое состояние соответствует одному вопросу.
    """
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_gender = State()

    # Состояние для навигации по рациону (чтобы бот знал, что пользователь уже получил план)
    viewing_plan = State()
