from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from logger import log
from states import UserDataForm
from keyboards import get_gender_keyboard, get_plan_navigation_keyboard
from gigachat_service import GigaChatService
import re

router = Router()
gigachat = GigaChatService()

# Хранилище планов в памяти (user_id -> данные)
user_plans_cache = {}


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    user_plans_cache.pop(message.from_user.id, None)

    await message.answer(
        "Привет! Я бот-нутрициолог 🥗.\n"
        "Я составлю для тебя персональный план питания на неделю.\n"
        "Для начала напиши свое имя:"
    )
    await state.set_state(UserDataForm.waiting_for_name)
    log.info(f"Пользователь {message.from_user.id} начал диалог")


@router.message(UserDataForm.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if not message.text:
        return
    await state.update_data(name=message.text)
    await message.answer("Отлично! Теперь напиши свой возраст (числом):")
    await state.set_state(UserDataForm.waiting_for_age)


@router.message(UserDataForm.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите возраст цифрами.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Теперь твой текущий вес в кг (например, 70.5):")
    await state.set_state(UserDataForm.waiting_for_weight)


@router.message(UserDataForm.waiting_for_weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        await state.update_data(weight=weight)
        await message.answer("Укажи свой рост в см (например, 175):")
        await state.set_state(UserDataForm.waiting_for_height)
    except ValueError:
        await message.answer("Вес должен быть числом. Попробуй еще раз.")


@router.message(UserDataForm.waiting_for_height)
async def process_height(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Рост должен быть числом.")
        return
    await state.update_data(height=int(message.text))

    await message.answer(
        "И последний вопрос: твой пол?",
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(UserDataForm.waiting_for_gender)


@router.callback_query(UserDataForm.waiting_for_gender, F.data.startswith("gender_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender_map = {"gender_male": "Мужской", "gender_female": "Женский"}
    gender = gender_map.get(callback.data)

    await state.update_data(gender=gender)
    data = await state.get_data()
    await state.clear()

    await callback.message.answer(
        f"Спасибо, {data['name']}! 📝\n"
        "Я анализирую твои данные и составляю рацион с помощью ИИ. Это займет около 10-15 секунд..."
    )
    await callback.answer()

    await generate_and_send_plan(callback.message, data, state)


async def generate_and_send_plan(message: types.Message, user_data: dict, state: FSMContext):
    """Генерирует план и подготавливает его к отправке."""
    try:
        full_plan_text = await gigachat.generate_diet_plan(user_data)

        # Парсим текст на страницы (по 2 дня на страницу)
        days = re.split(r'(### DAY \d+ ###)', full_plan_text)

        pages = []
        current_page_content = ""

        start_index = 1 if days and days[0] == '' else 0
        i = start_index

        while i < len(days):
            day_header = days[i]
            day_content = days[i + 1] if i + 1 < len(days) else ""

            current_page_content += f"{day_header}\n{day_content}\n\n"

            if any(x in day_header for x in ["DAY 2", "DAY 4", "DAY 6"]) or i + 2 >= len(days):
                pages.append(current_page_content)
                current_page_content = ""

            i += 2

        if not pages:
            pages = [full_plan_text]

        user_plans_cache[message.from_user.id] = {
            "pages": pages,
            "total_pages": len(pages)
        }

        await state.set_state(UserDataForm.viewing_plan)
        await send_plan_page(message, 0)

    except Exception as e:
        log.error(f"Ошибка генерации: {e}")
        await message.answer("Произошла ошибка при создании плана. Попробуйте /start позже.")


async def send_plan_page(message: types.Message, page_index: int):
    """Отправляет конкретную страницу плана."""
    user_id = message.from_user.id
    if user_id not in user_plans_cache:
        await message.answer("Данные плана не найдены. Пожалуйста, начните с /start")
        return

    cache = user_plans_cache[user_id]
    pages = cache["pages"]
    total = cache["total_pages"]

    if page_index < 0 or page_index >= total:
        return

    text = pages[page_index]
    header = f"📅 Рацион питания (Дни {(page_index * 2) + 1}-{min((page_index + 1) * 2, 7)})\n\n"

    await message.answer(
        header + text,
        reply_markup=get_plan_navigation_keyboard(page_index, total),
        parse_mode=None
    )


# Обработчики навигации
@router.callback_query(F.data.startswith("nav_next_"))
async def next_page(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Вперед'."""
    current_state = await state.get_state()
    if current_state != UserDataForm.viewing_plan.state:
        await callback.answer("Сначала заполните анкету", show_alert=True)
        return

    current_page = int(callback.data.split("_")[-1])
    await callback.message.delete()
    await send_plan_page(callback.message, current_page + 1)
    await callback.answer()


@router.callback_query(F.data.startswith("nav_prev_"))
async def prev_page(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад'."""
    current_state = await state.get_state()
    if current_state != UserDataForm.viewing_plan.state:
        await callback.answer("Сначала заполните анкету", show_alert=True)
        return

    current_page = int(callback.data.split("_")[-1])
    await callback.message.delete()
    await send_plan_page(callback.message, current_page - 1)
    await callback.answer()


@router.callback_query(F.data == "restart_bot")
async def restart_bot(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Начать заново'."""
    await callback.message.delete()
    user_plans_cache.pop(callback.from_user.id, None)
    await cmd_start(callback.message, state)
    await callback.answer()
