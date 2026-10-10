from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.keyboards.inline import get_faq_keyboard
from src.utils.text import START_TEXT

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    """Приветствие и клавиатура частых вопросов."""
    await message.answer(START_TEXT, reply_markup=get_faq_keyboard())