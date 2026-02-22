import logging
import sys


def setup_logger() -> logging.Logger:
    """
    Настраивает и возвращает объект логгера.
    Логи выводятся в консоль с цветом (если поддерживается) и уровнем INFO.
    """
    logger = logging.getLogger("nutrition_bot")
    logger.setLevel(logging.INFO)

    # Форматтер для красивого вывода логов
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Обработчик вывода в консоль (stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Добавляем обработчик к логгеру, если его еще нет
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# Создаем глобальный экземпляр логгера
log = setup_logger()
