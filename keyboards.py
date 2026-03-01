from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора пола."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Мужской", callback_data="gender_male")
    builder.button(text="Женский", callback_data="gender_female")
    builder.adjust(2)
    return builder.as_markup()


def get_favorites_keyboard(has_plan: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для главного меню.
    """
    builder = InlineKeyboardBuilder()

    if has_plan:
        builder.button(text="📋 Использовать последний план", callback_data="use_last_plan")
        builder.button(text="✨ Создать новый план", callback_data="create_new_plan")
    else:
        builder.button(text="🚀 Начать расчет", callback_data="create_new_plan")

    builder.button(text="⭐ Избранное", callback_data="view_favorites")
    builder.adjust(1, 1)

    return builder.as_markup()


def get_favorites_list_keyboard(favorites: list) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком избранных планов.

    Args:
        favorites: Список словарей с данными планов из БД
    """
    builder = InlineKeyboardBuilder()

    for fav in favorites:
        plan_id = fav['id']
        plan_date = fav['created_at'][:10]
        builder.button(
            text=f"📄 План #{plan_id} от {plan_date}",
            callback_data=f"view_favorite_{plan_id}"
        )

    builder.button(text="🔙 Назад в меню", callback_data="restart_bot")
    builder.adjust(1)

    return builder.as_markup()


def get_plan_navigation_keyboard(current_page: int, total_pages: int,
                                 is_favorite: bool = False, plan_id: int = None) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации по дням рациона с кнопкой избранного.
    """
    builder = InlineKeyboardBuilder()

    # Кнопка "Назад"
    if current_page > 0:
        builder.button(text="⬅️ Пред. день", callback_data=f"nav_prev_{current_page}")

    # Кнопка "Вперед"
    if current_page < total_pages - 1:
        builder.button(text="След. день ➡️", callback_data=f"nav_next_{current_page}")

    # Кнопка "Избранное" (только если есть plan_id)
    if plan_id:
        if is_favorite:
            builder.button(text="💔 Удалить из избранного",
                           callback_data=f"toggle_favorite_remove_{plan_id}_{current_page}")
        else:
            builder.button(text="⭐ В избранное",
                           callback_data=f"toggle_favorite_add_{plan_id}_{current_page}")

    # Кнопка "Начать заново"
    builder.button(text="🔄 Меню", callback_data="restart_bot")

    builder.adjust(2, 2, 1)

    return builder.as_markup()
