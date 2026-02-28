from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора пола."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Мужской", callback_data="gender_male")
    builder.button(text="Женский", callback_data="gender_female")
    builder.adjust(2)
    return builder.as_markup()


def get_plan_navigation_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации по дням рациона.
    current_page: текущая страница (0 = День 1, 1 = День 2 и т.д.)
    total_pages: всего страниц (7 дней = 7 страниц)
    """
    builder = InlineKeyboardBuilder()

    # Кнопка "Назад"
    if current_page > 0:
        builder.button(text="⬅️ Пред. день", callback_data=f"nav_prev_{current_page}")

    # Кнопка "Вперед"
    if current_page < total_pages - 1:
        builder.button(text="След. день ➡️", callback_data=f"nav_next_{current_page}")

    # Кнопка "Начать заново"
    builder.button(text="🔄 Новый расчет", callback_data="restart_bot")

    builder.adjust(2, 1)  # Расположение кнопок
    return builder.as_markup()
