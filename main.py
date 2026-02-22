import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from logger import log
from handlers import router


async def main():
    """Основная функция запуска бота."""
    log.info("Запуск бота 'Нутрициолог'...")

    # ✅ Инициализируем хранилище для FSM (память)
    # Для продакшена лучше использовать RedisStorage
    storage = MemoryStorage()

    # Инициализация бота
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    # ✅ Передаем storage и key в Dispatcher
    dp = Dispatcher(storage=storage, key=Config.BOT_TOKEN)

    # Удаляем вебхук (чтобы работал polling)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Вебхук удален (если существовал)")
    except Exception as e:
        log.warning(f"Не удалось удалить вебхук: {e}")

    # Регистрируем роутер с хендлерами
    dp.include_router(router)

    try:
        log.info("Запуск polling режима...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        log.info("Бот остановлен пользователем")
    except Exception as e:
        log.error(f"Критическая ошибка в работе бота: {e}")
    finally:
        await bot.session.close()
        log.info("Сессия бота закрыта")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
