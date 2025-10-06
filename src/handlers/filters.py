from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from src.storage import Storage

router = Router(name="filters")


# ---------- Keyboard ----------
def kb_filters() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 List keywords")],
            [KeyboardButton(text="➕ Add keyword"), KeyboardButton(text="➖ Remove keyword")],
            [KeyboardButton(text="🚫 Mute source"), KeyboardButton(text="✅ Unmute source")],
            [KeyboardButton(text="⬅️ Back")],
        ],
        resize_keyboard=True
    )


# ---------- States ----------
class AddKW(StatesGroup):
    waiting = State()


class RmKW(StatesGroup):
    waiting = State()


class MuteSrc(StatesGroup):
    waiting = State()


class UnmuteSrc(StatesGroup):
    waiting = State()


@router.message(F.text.casefold().in_({"⚙️ filters", "фильтры"}))
@router.message(Command("filters"))
async def cmd_filters(message: Message, storage: Storage, tg_channels: list[str] | None = None):
    user_id = message.from_user.id
    words = await storage.list_keywords(user_id)
    muted = await storage.list_muted_sources(user_id)
    channels = ", ".join(tg_channels or [])
    await message.answer(
        "Personal filters:\n"
        f"- Keywords: {', '.join(words) if words else 'none'}\n"
        f"- Muted sources: {', '.join(muted) if muted else 'none'}\n\n"
        "Use the buttons below or commands:\n"
        "/addkw word, /rmkw word, /listkw, /mute source, /unmute source, /muted\n\n"
        f"Available sources: {channels if channels else '—'}",
        reply_markup=kb_filters()
    )


@router.message(Command("listkw"))
async def cmd_listkw(message: Message, storage: Storage):
    words = await storage.list_keywords(message.from_user.id)
    await message.answer("Keywords: " + (", ".join(words) if words else "none"))

@router.message(Command("addkw"))
async def cmd_addkw(message: Message, storage: Storage):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Provide a word: /addkw word")
    kw = parts[1].strip().lower()
    await storage.add_keyword(message.from_user.id, kw)
    await message.answer(f"Added keyword: {kw}")

@router.message(Command("rmkw"))
async def cmd_rmkw(message: Message, storage: Storage):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Provide a word: /rmkw word")
    kw = parts[1].strip().lower()
    await storage.remove_keyword(message.from_user.id, kw)
    await message.answer(f"Removed keyword: {kw}")

@router.message(Command("mute"))
async def cmd_mute(message: Message, storage: Storage):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Provide a source: /mute tengrinews")
    src = parts[1].strip().lower().lstrip("@")
    await storage.mute_source(message.from_user.id, src)
    await message.answer(f"Muted source: {src}")

@router.message(Command("unmute"))
async def cmd_unmute(message: Message, storage: Storage):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Provide a source: /unmute tengrinews")
    src = parts[1].strip().lower().lstrip("@")
    await storage.unmute_source(message.from_user.id, src)
    await message.answer(f"Unmuted source: {src}")

@router.message(Command("muted"))
async def cmd_muted(message: Message, storage: Storage):
    muted = await storage.list_muted_sources(message.from_user.id)
    await message.answer("Muted sources: " + (", ".join(muted) if muted else "none"))


# ---------- Buttons (FSM) ----------
@router.message(F.text.casefold() == "➕ add keyword")
async def addkw_btn(message: Message, state: FSMContext):
    await state.set_state(AddKW.waiting)
    await message.answer("Send a keyword to add (or /cancel).")

@router.message(F.text.casefold() == "➖ remove keyword")
async def rmkw_btn(message: Message, state: FSMContext):
    await state.set_state(RmKW.waiting)
    await message.answer("Send a keyword to remove (or /cancel).")

@router.message(F.text.casefold() == "📝 list keywords")
async def listkw_btn(message: Message, storage: Storage):
    words = await storage.list_keywords(message.from_user.id)
    await message.answer("Keywords: " + (", ".join(words) if words else "none"))

@router.message(F.text.casefold() == "🚫 mute source")
async def mute_btn(message: Message, state: FSMContext):
    await state.set_state(MuteSrc.waiting)
    await message.answer("Send a source to mute, e.g. tengrinews (or /cancel).")

@router.message(F.text.casefold() == "✅ unmute source")
async def unmute_btn(message: Message, state: FSMContext):
    await state.set_state(UnmuteSrc.waiting)
    await message.answer("Send a source to unmute, e.g. tengrinews (or /cancel).")

# ---------- FSM: data input ----------
@router.message(AddKW.waiting, F.text)
async def addkw_enter(message: Message, storage: Storage, state: FSMContext):
    kw = (message.text or "").strip().lower()
    if not kw:
        return await message.answer("Please send a non-empty keyword.")
    await storage.add_keyword(message.from_user.id, kw)
    await state.clear()
    await message.answer(f"Added keyword: {kw}", reply_markup=kb_filters())

@router.message(RmKW.waiting, F.text)
async def rmkw_enter(message: Message, storage: Storage, state: FSMContext):
    kw = (message.text or "").strip().lower()
    if not kw:
        return await message.answer("Please send a non-empty keyword.")
    await storage.remove_keyword(message.from_user.id, kw)
    await state.clear()
    await message.answer(f"Removed keyword: {kw}", reply_markup=kb_filters())

@router.message(MuteSrc.waiting, F.text)
async def mute_enter(message: Message, storage: Storage, state: FSMContext):
    src = (message.text or "").strip().lower().lstrip("@")
    if not src:
        return await message.answer("Please send a source (e.g. tengrinews).")
    await storage.mute_source(message.from_user.id, src)
    await state.clear()
    await message.answer(f"Muted source: {src}", reply_markup=kb_filters())

@router.message(UnmuteSrc.waiting, F.text)
async def unmute_enter(message: Message, storage: Storage, state: FSMContext):
    src = (message.text or "").strip().lower().lstrip("@")
    if not src:
        return await message.answer("Please send a source (e.g. tengrinews).")
    await storage.unmute_source(message.from_user.id, src)
    await state.clear()
    await message.answer(f"Unmuted source: {src}", reply_markup=kb_filters())

# ---------- Cancel ----------
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.", reply_markup=kb_filters())
