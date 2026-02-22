import os
import sys
from dotenv import load_dotenv
from logger import log

# Явно указываем путь к файлу .env относительно текущего файла
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Загружаем переменные
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    log.info(f".env файл найден по пути: {ENV_PATH}")
else:
    log.error(f".env файл НЕ найден по пути: {ENV_PATH}")
    log.error(f"Текущая рабочая директория: {os.getcwd()}")


class Config:
    """Класс для хранения конфигурации приложения."""
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    GIGA_API_KEY: str = os.getenv("GIGA_API_KEY")
    GIGA_CERT_PATH: str = os.getenv("GIGA_CERT_PATH")

    # Валидация при загрузке
    if not BOT_TOKEN:
        log.error("Критическая ошибка: BOT_TOKEN не найден в окружении!")
        print("\n❌ ОШИБКА: Переменная BOT_TOKEN пуста или не найдена.")
        print("1. Проверьте, что файл .env лежит в корне проекта.")
        print("2. Проверьте, что нет пробелов вокруг знака '=' в файле .env.")
        print("3. Убедитесь, что токен скопирован полностью из @BotFather.\n")
        sys.exit(1)

    if not GIGA_API_KEY:
        log.error("Критическая ошибка: GIGA_API_KEY не найден в окружении!")
        print("\n❌ ОШИБКА: Переменная GIGA_API_KEY пуста или не найдена.")
        print("1. Получите API ключ в кабинете разработчика Сбера.")
        print("2. Добавьте его в файл .env\n")
        sys.exit(1)

    # Проверка сертификата (опционально, может быть не обязателен)
    if GIGA_CERT_PATH and not os.path.exists(GIGA_CERT_PATH):
        log.warning(f"Сертификат не найден по пути: {GIGA_CERT_PATH}")
        log.warning("Работа с GigaChat может быть невозможна без сертификата")

    log.info("Конфигурация успешно загружена")
