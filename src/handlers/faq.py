"""Ответы на нажатия кнопок FAQ-меню."""

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from src.keyboards.inline import FaqCallback, get_faq_keyboard
from src.utils.text import FAQ_ANSWERS

router = Router()


@router.callback_query(FaqCallback.filter())
async def show_answer(callback: CallbackQuery, callback_data: FaqCallback) -> None:
    """Показывает ответ и возвращает меню под ним, чтобы можно было спросить ещё."""
    answer = FAQ_ANSWERS.get(callback_data.action)
    if answer is None:
        await callback.answer("Этот раздел пока недоступен", show_alert=True)
        return

    # Сразу убираем «часики» на кнопке.
    await callback.answer()

    # Сообщение может быть недоступно (слишком старое) - тогда править нечего.
    if not isinstance(callback.message, Message):
        return

    try:
        await callback.message.edit_text(answer, reply_markup=get_faq_keyboard())
    except TelegramBadRequest as error:
        # Повторное нажатие на ту же кнопку: текст не изменился, это не ошибка.
        if "message is not modified" not in str(error):
            raise