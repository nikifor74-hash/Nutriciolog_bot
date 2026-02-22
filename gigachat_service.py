from gigachat import GigaChat
from config import Config
from logger import log
import asyncio
import os

# Системный промт для нейросети
SYSTEM_PROMPT = """
Ты профессиональный нутрициолог и диетолог с 20-летним стажем. 
Твоя задача — составить сбалансированный рацион питания на 7 дней на основе данных пользователя.

Инструкции:
1. Рассчитай примерную норму калорий (BMR/TDEE) исходя из веса, роста, возраста и пола.
2. Составь меню на 7 дней (Завтрак, Обед, Ужин, Перекус).
3. Блюда должны быть разнообразными, доступными и полезными.
4. В конце каждого дня добавь краткий комментарий по нутриентам (белки, жиры, углеводы).

Формат ответа должен быть СТРОГО следующим (используй маркеры ### DAY X ### для разделения):

### DAY 1 ###
[Меню первого дня]

### DAY 2 ###
[Меню второго дня]

... и так далее до 7 дня.

Не пиши никаких вступительных слов. Начинай сразу с ### DAY 1 ###.
Используй только простой текст без Markdown форматирования (без *, _, `, ~).
"""


class GigaChatService:
    def __init__(self):
        """
        Инициализация клиента GigaChat с использованием API ключа.
        """
        try:
            # Подготовка параметров для клиента
            client_kwargs = {
                "credentials": Config.GIGA_API_KEY,
                "model": "GigaChat-Pro",
                "timeout": 60,
            }

            # Проверяем сертификат
            if Config.GIGA_CERT_PATH and os.path.exists(Config.GIGA_CERT_PATH):
                client_kwargs["cert"] = Config.GIGA_CERT_PATH
                client_kwargs["verify_ssl_certs"] = False
                log.info(f"Используется сертификат: {Config.GIGA_CERT_PATH}")
            else:
                # Отключаем проверку SSL для самоподписанных сертификатов
                client_kwargs["verify_ssl_certs"] = False
                log.warning("Проверка SSL отключена. Используйте сертификат в продакшене!")

            # Инициализация клиента GigaChat
            self.client = GigaChat(**client_kwargs)
            log.info("GigaChat клиент успешно инициализирован")

        except Exception as e:
            log.error(f"Ошибка инициализации GigaChat клиента: {e}")
            raise

    async def generate_diet_plan(self, user_data: dict) -> str:
        """
        Отправляет данные пользователя в GigaChat и получает план питания.

        Args:
            user_ Словарь с данными пользователя (name, age, weight, height, gender)

        Returns:
            str: Текст плана питания от GigaChat
        """
        user_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:\n"
            f"Имя: {user_data['name']}\n"
            f"Пол: {user_data['gender']}\n"
            f"Возраст: {user_data['age']} лет\n"
            f"Вес: {user_data['weight']} кг\n"
            f"Рост: {user_data['height']} см\n\n"
            f"Составь подробный план питания на 7 дней."
        )

        try:
            log.info(f"Отправка запроса в GigaChat для пользователя {user_data.get('name')}")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._call_gigachat,
                user_prompt
            )

            if response and hasattr(response, 'choices') and response.choices:
                plan_text = response.choices[0].message.content
                log.info("План питания успешно получен от GigaChat")
                return plan_text
            elif isinstance(response, str):
                return response
            else:
                log.warning(f"GigaChat вернул неожиданный формат: {type(response)}")
                return "Не удалось получить план питания. Попробуйте позже."

        except Exception as e:
            log.error(f"Ошибка при запросе к GigaChat: {type(e).__name__} - {e}")
            return f"Произошла ошибка при генерации плана: {str(e)}"

    def _call_gigachat(self, prompt: str):
        """
        Внутренний метод для вызова GigaChat API.
        Минимальный вызов для максимальной совместимости.
        """
        # ✅ Вызов только с prompt - работает со всеми версиями
        return self.client.chat(prompt)