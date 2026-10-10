"""Inline-клавиатуры бота.

Подписи кнопок и их идентификаторы (action) лежат здесь.
Тексты ответов на эти кнопки лежат в src/utils/text.py (FAQ_ANSWERS),
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class FaqCallback(CallbackData, prefix="faq"):
    """Данные, которые приходят в бота при нажатии кнопки FAQ."""

    action: str


# (action, подпись кнопки) в том порядке, в котором кнопки идут в меню.
FAQ_BUTTONS: tuple[tuple[str, str], ...] = (
    ("services", "🌐 Услуги и возможности Tilda"),
    ("pricing", "💰 Стоимость разработки сайта"),
    ("stages", "🛠 Этапы и сроки работы"),
    ("about", "📋 Информация обо мне"),
    ("other", "💬 Ответы на другие вопросы"),
)

# Раскладка «таблицей»: сколько кнопок в каждом ряду (сумма = число кнопок).
# Подписи длинные, поэтому по одной кнопке в ряду, кнопки во всю ширину.
# Хотите сетку из двух столбцов - поставьте (2, 2, 1).
FAQ_LAYOUT: tuple[int, ...] = (1, 1, 1, 1, 1)


def get_faq_keyboard() -> InlineKeyboardMarkup:
    """Меню частых вопросов.

    Показывается под приветствием (/start) и под каждым ответом,
    чтобы пользователь мог сразу задать следующий вопрос.
    """
    builder = InlineKeyboardBuilder()
    for action, text in FAQ_BUTTONS:
        builder.button(text=text, callback_data=FaqCallback(action=action))
    builder.adjust(*FAQ_LAYOUT)
    return builder.as_markup()