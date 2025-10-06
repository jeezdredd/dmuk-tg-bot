import asyncio
from typing import List

from aiogram import Router, F
from aiogram.types import Message, InputMediaPhoto, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from src.storage import Storage
from src.services.telegram_fetcher import TelegramFetcher

router = Router(name="admin")

# Buttons
BTN_SOURCES = "📚 Sources"
BTN_REFETCH = "🔄 Refetch"
BTN_BROADCAST = "📣 Broadcast"
BTN_BACK = "⬅️ Back"

# Broadcast submenu
BTN_BC_TEXT = "📝 Text"
BTN_BC_MEDIA = "🖼 Media"

# Text broadcast actions
BTN_TXT_EDIT = "🖊 Edit text"
BTN_TXT_SEND = "✅ Send"
BTN_TXT_CANCEL = "❌ Cancel"

# Media broadcast actions
BTN_MEDIA_ADD = "➕ Add photo"
BTN_MEDIA_SET_CAPTION = "🖊 Set caption"
BTN_MEDIA_CLEAR = "🗑 Clear"
BTN_MEDIA_SEND = "📨 Send"
BTN_MEDIA_CANCEL = "❌ Cancel"

# Refetch quick options
REFETCH_CHOICES = ["5", "10", "20", "50"]


def is_admin(message: Message, admin_ids: set[int]) -> bool:
    return message.from_user and message.from_user.id in admin_ids


# Keyboards
def kb_admin_main() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SOURCES), KeyboardButton(text=BTN_REFETCH)],
            [KeyboardButton(text=BTN_BROADCAST)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True
    )


def kb_broadcast_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BC_TEXT), KeyboardButton(text=BTN_BC_MEDIA)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True
    )


def kb_text_actions(has_text: bool) -> ReplyKeyboardMarkup:
    rows = []
    if has_text:
        rows.append([KeyboardButton(text=BTN_TXT_SEND)])
    rows.append([KeyboardButton(text=BTN_TXT_EDIT)])
    rows.append([KeyboardButton(text=BTN_TXT_CANCEL), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def kb_media_actions() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MEDIA_ADD), KeyboardButton(text=BTN_MEDIA_SET_CAPTION)],
            [KeyboardButton(text=BTN_MEDIA_CLEAR)],
            [KeyboardButton(text=BTN_MEDIA_SEND)],
            [KeyboardButton(text=BTN_MEDIA_CANCEL), KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True
    )


def kb_refetch_choices() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="5"), KeyboardButton(text="10"), KeyboardButton(text="20"), KeyboardButton(text="50")],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True
    )


# FSM
class RefetchFSM(StatesGroup):
    choosing = State()


class BroadcastText(StatesGroup):
    waiting_text = State()


class BroadcastMedia(StatesGroup):
    collecting = State()
    waiting_caption = State()


# Admin main (optional)
@router.message(Command("admin"))
async def open_admin_cmd(message: Message, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    await message.answer("🛠 Admin panel:", reply_markup=kb_admin_main())


# Sources
@router.message(F.text == BTN_SOURCES)
@router.message(Command("sources"))
async def cmd_sources(message: Message, admin_ids: set[int], telegram_fetcher: TelegramFetcher | None = None):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    if not telegram_fetcher:
        return await message.answer("Telethon is not configured or not running.")
    await message.answer("Connected channels: " + ", ".join(telegram_fetcher.channels), reply_markup=kb_admin_main())


# Refetch via buttons
@router.message(F.text == BTN_REFETCH)
async def refetch_btn(message: Message, state: FSMContext, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    await state.set_state(RefetchFSM.choosing)
    await message.answer("Choose how many posts to refetch per channel:", reply_markup=kb_refetch_choices())


@router.message(RefetchFSM.choosing, F.text.in_(REFETCH_CHOICES))
async def refetch_choice(message: Message, state: FSMContext, admin_ids: set[int], telegram_fetcher: TelegramFetcher | None):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    n = int(message.text)
    await state.clear()
    if not telegram_fetcher:
        return await message.answer("Telethon not running.", reply_markup=kb_admin_main())
    await message.answer(f"Fetching last {n} messages per channel…")
    await telegram_fetcher.backfill_recent(per_channel=n)
    await message.answer("Done. See /news.", reply_markup=kb_admin_main())


@router.message(RefetchFSM.choosing, F.text)
async def refetch_ignore(message: Message):
    await message.answer("Please choose using buttons.")


# Broadcast main menu
@router.message(F.text == BTN_BROADCAST)
@router.message(Command("broadcast"))
async def cmd_broadcast_info(message: Message, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    await message.answer("Broadcast menu:", reply_markup=kb_broadcast_menu())


# Broadcast Text flow (buttons)
@router.message(F.text == BTN_BC_TEXT)
async def bc_text_enter(message: Message, state: FSMContext, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    await state.set_state(BroadcastText.waiting_text)
    await state.update_data(text=None)
    await message.answer(
        "Send the broadcast text as a message.\nWhen ready, press ✅ Send.\nYou can press 🖊 Edit text to replace it.",
        reply_markup=kb_text_actions(has_text=False)
    )

@router.message(BroadcastText.waiting_text, F.text == BTN_TXT_EDIT)
async def bc_text_edit_again(message: Message, state: FSMContext):
    await state.update_data(text=None)
    await message.answer("Send new text for the broadcast.", reply_markup=kb_text_actions(has_text=False))

@router.message(BroadcastText.waiting_text, F.text == BTN_TXT_CANCEL)
async def bc_text_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.", reply_markup=kb_broadcast_menu())

@router.message(BroadcastText.waiting_text, F.text == BTN_BACK)
async def bc_text_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Back.", reply_markup=kb_broadcast_menu())

# ВАЖНО: отправка должна стоять ДО общего обработчика текста
@router.message(BroadcastText.waiting_text, F.text == BTN_TXT_SEND)
async def bc_text_send(message: Message, state: FSMContext, storage: Storage, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    data = await state.get_data()
    text = data.get("text")
    if not text:
        return await message.answer("No text yet. Send the message first.", reply_markup=kb_text_actions(has_text=False))

    await state.clear()
    user_ids = await storage.get_all_user_ids()
    ok = 0
    failed = 0
    await message.answer(f"Starting broadcast to {len(user_ids)} users…")

    for uid in user_ids:
        try:
            await message.bot.send_message(uid, text, disable_web_page_preview=False)
            ok += 1
            await asyncio.sleep(0.03)
        except Exception:
            failed += 1

    await message.answer(f"Broadcast finished. Success: {ok}, failed: {failed}.", reply_markup=kb_broadcast_menu())

# Общий обработчик текста — ДОЛЖЕН быть ПОСЛЕ отправки; игнорируем кнопки
@router.message(BroadcastText.waiting_text, F.text)
async def bc_text_catch_text(message: Message, state: FSMContext, admin_ids: set[int]):
    # Если прилетела одна из кнопок — игнор
    if message.text in {BTN_TXT_SEND, BTN_TXT_EDIT, BTN_TXT_CANCEL, BTN_BACK}:
        return
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    await state.update_data(text=message.text)
    await message.answer(f"Preview:\n\n{message.text}", reply_markup=kb_text_actions(has_text=True))


# Broadcast Media flow (buttons)
@router.message(F.text == BTN_BC_MEDIA)
async def bc_media_start(message: Message, state: FSMContext, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.answer("Admins only.")
    await state.set_state(BroadcastMedia.collecting)
    await state.update_data(photos=[], caption=None)
    await message.answer(
        "Media broadcast mode.\n"
        "Use buttons to add photos or set caption.\n"
        "When ready, press 📨 Send.",
        reply_markup=kb_media_actions()
    )

@router.message(BroadcastMedia.collecting, F.text == BTN_MEDIA_ADD)
async def bc_media_add_hint(message: Message):
    await message.answer("Send one or more photos now (max 10). Each photo you send will be added.", reply_markup=kb_media_actions())

@router.message(BroadcastMedia.collecting, F.text == BTN_MEDIA_SET_CAPTION)
async def bc_media_set_caption(message: Message, state: FSMContext):
    await state.set_state(BroadcastMedia.waiting_caption)
    await message.answer("Send a caption text.", reply_markup=kb_media_actions())

@router.message(BroadcastMedia.waiting_caption, F.text)
async def bc_media_capture_caption(message: Message, state: FSMContext):
    data = await state.get_data()
    photos: List[str] = data.get("photos") or []
    await state.update_data(caption=message.text, photos=photos)
    await state.set_state(BroadcastMedia.collecting)
    await message.answer("Caption saved.", reply_markup=kb_media_actions())

@router.message(BroadcastMedia.collecting, F.text == BTN_MEDIA_CLEAR)
async def bc_media_clear(message: Message, state: FSMContext):
    await state.update_data(photos=[], caption=None)
    await message.answer("Cleared photos and caption.", reply_markup=kb_media_actions())

@router.message(BroadcastMedia.collecting, F.text == BTN_MEDIA_SEND)
async def bc_media_send(message: Message, state: FSMContext, storage: Storage, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.reply("Admins only.")
    data = await state.get_data()
    photos: List[str] = data.get("photos") or []
    caption: str | None = data.get("caption")

    if not photos:
        return await message.answer("You haven’t added any photos. Use ➕ Add photo.", reply_markup=kb_media_actions())

    await state.clear()
    user_ids = await storage.get_all_user_ids()
    ok = 0
    failed = 0
    await message.answer(f"Sending {len(photos)} photo(s) to {len(user_ids)} users…")

    bot = message.bot

    if len(photos) == 1:
        for uid in user_ids:
            try:
                await bot.send_photo(uid, photos[0], caption=caption)
                ok += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
    else:
        media_group = []
        for i, fid in enumerate(photos[:10]):  # telegram limit is 10
            if i == 0 and caption:
                media_group.append(InputMediaPhoto(media=fid, caption=caption))
            else:
                media_group.append(InputMediaPhoto(media=fid))
        for uid in user_ids:
            try:
                await bot.send_media_group(uid, media_group)
                ok += 1
                await asyncio.sleep(0.08)
            except Exception:
                failed += 1

    await message.answer(f"Broadcast finished. Success: {ok}, failed: {failed}.", reply_markup=kb_broadcast_menu())

@router.message(BroadcastMedia.collecting, F.text.in_({BTN_MEDIA_CANCEL, BTN_BACK}))
@router.message(BroadcastMedia.waiting_caption, F.text.in_({BTN_MEDIA_CANCEL, BTN_BACK}))
async def bc_media_cancel_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.", reply_markup=kb_broadcast_menu())

@router.message(BroadcastMedia.collecting, F.photo)
async def collect_photo(message: Message, state: FSMContext, admin_ids: set[int]):
    if not is_admin(message, admin_ids):
        return await message.reply("Admins only.")
    data = await state.get_data()
    photos: List[str] = data.get("photos") or []
    if len(photos) >= 10:
        return await message.answer("Max photos reached (10). Press 📨 Send or use 🗑 Clear.", reply_markup=kb_media_actions())

    file_id = message.photo[-1].file_id
    photos.append(file_id)

    await state.update_data(photos=photos)
    await message.answer(f"Photo added ({len(photos)}/10). You can add more or press 📨 Send.", reply_markup=kb_media_actions())