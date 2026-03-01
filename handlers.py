import re

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from gigachat_service import GigaChatService
from keyboards import (
    get_gender_keyboard,
    get_plan_navigation_keyboard,
    get_favorites_keyboard,
    get_favorites_list_keyboard
)
from logger import log
from states import UserDataForm

router = Router()
gigachat = GigaChatService()
user_plans_cache = {}


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    db.add_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    last_plan = db.get_last_diet_plan(user_id)

    if last_plan and last_plan.get('plan_text') and len(last_plan.get('plan_text', '')) > 100:
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            f"У вас уже есть сохраненный план питания.\n\n"
            f"Выберите действие:",
            reply_markup=get_favorites_keyboard(has_plan=True)
        )
    else:
        await message.answer(
            f"Привет, {message.from_user.first_name}! 🥗\n"
            f"Я бот-нутрициолог. Составлю для тебя персональный план питания на неделю.\n"
            f"Для начала напиши свое имя:"
        )
        await state.set_state(UserDataForm.waiting_for_name)

    log.info(f"Пользователь {user_id} начал диалог")


@router.callback_query(F.data == "use_last_plan")
async def use_last_plan(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id

    last_plan = db.get_last_diet_plan(user_id)

    if last_plan and last_plan.get('plan_text') and len(last_plan.get('plan_text', '')) > 100:
        await state.set_state(UserDataForm.viewing_plan)

        pages = parse_plan_to_pages(last_plan['plan_text'])
        if not pages:
            pages = [last_plan['plan_text']]

        user_plans_cache[user_id] = {
            "pages": pages,
            "total_pages": len(pages),
            "plan_id": last_plan['id'],
            "from_db": True
        }

        log.info(f"План #{last_plan['id']} загружен из БД для пользователя {user_id}")
        # ✅ ПЕРЕДАЕМ user_id ЯВНО
        await send_plan_page(callback.message, 0, user_id)
    else:
        await callback.message.answer(
            "⚠️ Сохраненный план поврежден или отсутствует.\n"
            "Давайте создадим новый!"
        )
        await state.set_state(UserDataForm.waiting_for_name)
        await callback.message.answer("Для начала напиши свое имя:")

    await callback.answer()


@router.callback_query(F.data == "create_new_plan")
async def create_new_plan(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Отлично! Для начала напиши свое имя:")
    await state.set_state(UserDataForm.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data == "view_favorites")
async def view_favorites(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    favorites = db.get_favorites(user_id)

    if not favorites:
        await callback.message.answer(
            "📭 У вас пока нет избранных планов.\n\n"
            "Когда вы получите план питания, вы сможете сохранить его в избранное."
        )
    else:
        await callback.message.answer(
            f"⭐ Избранные планы ({len(favorites)}):\n\n"
            + "\n".join([f"📌 План #{fav['id']} от {fav['created_at'][:10]}" for fav in favorites]),
            reply_markup=get_favorites_list_keyboard(favorites)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("view_favorite_"))
async def view_favorite_plan(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    plan_id = int(callback.data.split("_")[-1])

    plan = db.get_diet_plan(plan_id)

    if plan and plan.get('plan_text') and len(plan.get('plan_text', '')) > 100:
        await state.set_state(UserDataForm.viewing_plan)

        pages = parse_plan_to_pages(plan['plan_text'])
        if not pages:
            pages = [plan['plan_text']]

        user_plans_cache[user_id] = {
            "pages": pages,
            "total_pages": len(pages),
            "plan_id": plan['id'],
            "from_db": True
        }

        log.info(f"Избранный план #{plan_id} открыт пользователем {user_id}")
        # ✅ ПЕРЕДАЕМ user_id ЯВНО
        await send_plan_page(callback.message, 0, user_id)
    else:
        await callback.message.answer("❌ Не удалось загрузить план. Попробуйте другой.")

    await callback.answer()


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

    profile_id = db.save_user_profile(callback.from_user.id, data)
    await state.update_data(profile_id=profile_id)
    await state.clear()

    await callback.message.answer(
        f"Спасибо, {data['name']}! 📝\n"
        "Я анализирую твои данные и составляю рацион с помощью ИИ. Это займет около 10-15 секунд..."
    )
    await callback.answer()

    # ✅ ПЕРЕДАЕМ user_id ЯВНО
    await generate_and_send_plan(
        callback.message,
        data,
        state,
        profile_id,
        callback.from_user.id
    )


async def generate_and_send_plan(message, user_data, state, profile_id, user_id):
    try:
        full_plan_text = await gigachat.generate_diet_plan(user_data)
        log.info(f"Получен план длиной {len(full_plan_text)} символов")

        if len(full_plan_text) < 100:
            log.error("Ответ от GigaChat слишком короткий")
            await message.answer("⚠️ Не удалось получить план питания. Попробуйте позже.")
            return

        if "ошибка" in full_plan_text.lower() or "error" in full_plan_text.lower():
            log.error("Ответ от GigaChat содержит ошибку")
            await message.answer("⚠️ Не удалось получить план питания. Попробуйте позже.")
            return

        plan_id = db.save_diet_plan(
            user_id=user_id,
            profile_id=profile_id or 0,
            plan_text=full_plan_text,
            days_count=7
        )

        log.info(f"План сохранен в БД с ID: {plan_id} для пользователя {user_id}")

        pages = parse_plan_to_pages(full_plan_text)
        if not pages:
            pages = [full_plan_text]

        user_plans_cache[user_id] = {
            "pages": pages,
            "total_pages": len(pages),
            "plan_id": plan_id,
            "from_db": False
        }

        await state.set_state(UserDataForm.viewing_plan)
        # ✅ ПЕРЕДАЕМ user_id ЯВНО
        await send_plan_page(message, 0, user_id)

    except Exception as e:
        log.error(f"Ошибка генерации: {e}")
        await message.answer("Произошла ошибка при создании плана. Попробуйте /start позже.")


def parse_plan_to_pages(plan_text):
    days = re.split(r'(### ДЕНЬ \d+ ###)', plan_text)
    if len(days) <= 1:
        days = re.split(r'(### DAY \d+ ###)', plan_text)

    pages = []
    start_index = 1 if days and days[0] == '' else 0
    i = start_index

    while i < len(days):
        day_header = days[i]
        day_content = days[i + 1] if i + 1 < len(days) else ""
        pages.append(f"{day_header}\n{day_content}\n")
        i += 2

    return pages if pages else [plan_text]


async def send_plan_page(message, page_index, user_id):
    """✅ user_id передаётся ОБЯЗАТЕЛЬНО"""
    if user_id not in user_plans_cache:
        log.error(f"План не найден в кэше для user_id={user_id}. Доступные: {list(user_plans_cache.keys())}")
        await message.answer("Данные плана не найдены. Пожалуйста, начните с /start")
        return

    cache = user_plans_cache[user_id]
    pages = cache["pages"]
    total = cache["total_pages"]
    plan_id = cache.get("plan_id")

    if page_index < 0 or page_index >= total:
        return

    text = pages[page_index]
    header = f"📅 Рацион питания (День {page_index + 1} из {total})\n\n"
    is_favorite = db.is_in_favorites(user_id, plan_id) if plan_id else False

    await message.answer(
        header + text,
        reply_markup=get_plan_navigation_keyboard(page_index, total, is_favorite, plan_id),
        parse_mode=None
    )


@router.callback_query(F.data.startswith("nav_next_"))
async def next_page(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != UserDataForm.viewing_plan.state:
        await callback.answer("Сначала заполните анкету", show_alert=True)
        return

    user_id = callback.from_user.id  # ✅ Получаем user_id из callback
    current_page = int(callback.data.split("_")[-1])
    await callback.message.delete()
    # ✅ ПЕРЕДАЕМ user_id ЯВНО
    await send_plan_page(callback.message, current_page + 1, user_id)
    await callback.answer()


@router.callback_query(F.data.startswith("nav_prev_"))
async def prev_page(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != UserDataForm.viewing_plan.state:
        await callback.answer("Сначала заполните анкету", show_alert=True)
        return

    user_id = callback.from_user.id
    current_page = int(callback.data.split("_")[-1])
    await callback.message.delete()
    # ✅ ПЕРЕДАЕМ user_id ЯВНО
    await send_plan_page(callback.message, current_page - 1, user_id)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_favorite_"))
async def toggle_favorite(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    action = parts[2]
    plan_id = int(parts[3])
    current_page = int(parts[4])

    if action == "add":
        db.add_to_favorites(user_id, plan_id)
        await callback.answer("✅ План добавлен в избранное!")
    else:
        db.remove_from_favorites(user_id, plan_id)
        await callback.answer("❌ План удален из избранного!")

    await callback.message.delete()
    # ✅ ПЕРЕДАЕМ user_id ЯВНО
    await send_plan_page(callback.message, current_page, user_id)


@router.callback_query(F.data == "restart_bot")
async def restart_bot(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user_id = callback.from_user.id
    user_plans_cache.pop(user_id, None)
    await state.clear()

    db.add_or_update_user(
        user_id=user_id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    last_plan = db.get_last_diet_plan(user_id)
    log.info(f"restart_bot: user_id={user_id}, last_plan={last_plan is not None}")

    if last_plan and last_plan.get('plan_text') and len(last_plan.get('plan_text', '')) > 100:
        await callback.message.answer(
            f"Привет, {callback.from_user.first_name}! 👋\n\n"
            f"У вас уже есть сохраненный план питания.\n\n"
            f"Выберите действие:",
            reply_markup=get_favorites_keyboard(has_plan=True)
        )
    else:
        await callback.message.answer(
            f"Привет, {callback.from_user.first_name}! 🥗\n"
            f"Я бот-нутрициолог. Составлю для тебя персональный план питания на неделю.\n"
            f"Для начала напиши свое имя:"
        )
        await state.set_state(UserDataForm.waiting_for_name)

    await callback.answer()
