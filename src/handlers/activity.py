from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from src.storage import Storage

router = Router(name="activity")

@router.message()
async def touch_on_message(message: Message, storage: Storage):
    if message.from_user:
        await storage.touch_user(message.from_user.id)

@router.callback_query()
async def touch_on_callback(cb: CallbackQuery, storage: Storage):
    if cb.from_user:
        await storage.touch_user(cb.from_user.id)