"""Точка входа: собирает бота воедино и запускает его.

Запуск из корня проекта:

    python -m src.main

Что делает этот файл:
1. читает BOT_TOKEN из файла .env (лежит в корне проекта);
2. собирает Dispatcher и подключает роутеры из src/handlers;
3. проверяет токен, регистрирует команды и запускает long polling;
4. корректно закрывает соединения при остановке (Ctrl+C).
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.types import BotCommand
from dotenv import load_dotenv

from src.handlers import faq, start

logger = logging.getLogger(__name__)

# .env лежит в корне проекта (на уровень выше папки src), поэтому ищем его
# по расположению этого файла, а не по текущей папке запуска.
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Команды, которые видят все пользователи в меню Telegram.
# /admin сюда намеренно не добавлена: она скрыта от обычных пользователей.
PUBLIC_COMMANDS: tuple[BotCommand, ...] = (
    BotCommand(command="start", description="Начать работу с ботом"),
)


def get_bot_token() -> str:
    """Читает BOT_TOKEN из .env и проверяет, что он заполнен.

    Переменные окружения, уже заданные в системе, имеют приоритет над .env
    (удобно для деплоя). Текст ошибки не содержит значения токена.
    """
    load_dotenv(ENV_PATH)
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            f"BOT_TOKEN не найден. Создайте файл {ENV_PATH} на основе "
            ".env.example и укажите токен от @BotFather: BOT_TOKEN=123456:ABC..."
        )
    return token


def build_dispatcher() -> Dispatcher:
    """Создаёт Dispatcher и подключает к нему все роутеры.

    Порядок подключения важен: апдейт получает первый подходящий обработчик.
    Отдельная функция (а не код внутри main) нужна, чтобы сборку можно было
    проверить в тестах без запуска бота.
    """
    dp = Dispatcher()

    # Сюда же добавляются новые части проекта по мере готовности этапов:
    #   этап 3: admin.router (фильтр IsAdmin), его нужно ставить до faq;
    #   этап 5: dp.message.middleware(...) / dp.callback_query.middleware(...)
    #           для антиспама и статистики.
    dp.include_routers(
        start.router,
        faq.router,
    )
    return dp


async def setup_bot(bot: Bot) -> None:
    """Подготовка бота к запуску: проверка токена, команды, очистка очереди."""
    me = await bot.get_me()  # заодно проверяет, что токен рабочий
    logger.info("Бот авторизован: @%s (id=%s)", me.username, me.id)

    await bot.set_my_commands(list(PUBLIC_COMMANDS))

    # Убираем вебхук (он мешает long polling) и старые апдейты, накопившиеся
    # пока бот был выключен, чтобы он не отвечал на устаревшие нажатия.
    await bot.delete_webhook(drop_pending_updates=True)


async def main() -> None:
    """Запускает бота и работает, пока его не остановят."""
    bot = Bot(token=get_bot_token())
    dp = build_dispatcher()

    try:
        await setup_bot(bot)
        logger.info("Запуск polling. Остановка: Ctrl+C")
        await dp.start_polling(
            bot,
            # Просим Telegram присылать только те типы апдейтов,
            # для которых в роутерах есть обработчики.
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        # Закрываем HTTP-сессию, иначе при остановке будет предупреждение
        # «Unclosed client session».
        await bot.session.close()
        logger.info("Бот остановлен")


def run() -> None:
    """Настраивает логирование и запускает main() с понятными сообщениями об ошибках."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as stop:
        # Ctrl+C - штатная остановка; SystemExit несёт текст про отсутствующий токен.
        if isinstance(stop, SystemExit) and stop.code not in (None, 0):
            logger.error("%s", stop.code)
            sys.exit(1)
    except TelegramUnauthorizedError:
        logger.error("Telegram отклонил токен. Проверьте BOT_TOKEN в .env.")
        sys.exit(1)
    except TelegramNetworkError as error:
        logger.error("Не удалось связаться с Telegram: %s", error.message)
        sys.exit(1)


if __name__ == "__main__":
    run()