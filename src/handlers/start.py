from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

from src.storage import Storage
from src.handlers.common_keyboards import kb_main

router = Router(name="start")

# Кнопки (EN/RU)
BTN_NEWS = {"📰 News", "Новости"}
BTN_SUB = {"🔔 Subscribe", "Подписаться"}
BTN_UNSUB = {"🔕 Unsubscribe", "Отписаться"}
BTN_FILTERS = {"⚙️ Filters", "Фильтры"}
BTN_HELP = {"❓ Help", "Помощь"}
BTN_ADMIN = {"🛠 Admin Panel", "Админ панель"}
BTN_BACK = {"⬅️ Back", "Назад"}
# Schedule/Profile обрабатываются в своих модулях:
# - src/handlers/schedule.py ловит F.text in {"📅 Schedule","Расписание"}
# - src/handlers/profile.py ловит F.text in {"👤 Profile","Профиль"}

def kb_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Sources"), KeyboardButton(text="🔄 Refetch")],
            [KeyboardButton(text="📣 Broadcast")],
            [KeyboardButton(text="⬅️ Back")],
        ],
        resize_keyboard=True
    )

@router.message(CommandStart())
async def cmd_start(message: Message, storage: Storage, admin_ids: set[int]):
    user_id = message.from_user.id
    is_admin = user_id in admin_ids
    await storage.add_or_update_user(user_id, is_admin=is_admin)
    subscribed = await storage.is_subscribed(user_id)
    text = (
        "👋 <b>Welcome to DMUK University Bot!</b>\n\n"
        "✨ Here you can:\n"
        "• 📰 Get the latest <b>news</b>\n"
        "• 📅 View your <b>schedule</b> by day\n"
        "• 👤 Manage your <b>student profile</b> (ID, name, photo)\n"
        "• 🔔 <b>Subscribe</b> to push notifications\n"
        "• ⚙️ Configure <b>filters</b> for news/sources\n"
        "• 🛠 Admin panel (for admins)\n\n"
        "Type /help or press a button below!"
    )
    await message.answer(text, reply_markup=kb_main(subscribed, is_admin), parse_mode="HTML")

@router.message(F.text.in_(BTN_HELP))
@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "❓ <b>Help</b>\n"
        "• /news — Latest news\n"
        "• /subscribe — Enable notifications\n"
        "• /unsubscribe — Disable notifications\n"
        "• /filters — Personal filters\n"
        "• /schedule — View your schedule\n"
        "• /profile — View/edit your student profile\n\n"
        "<b>Filters:</b>\n"
        "• /addkw word — Add keyword\n"
        "• /rmkw word — Remove keyword\n"
        "• /listkw — List keywords\n"
        "• /mute source — Mute source (e.g., tengrinews)\n"
        "• /unmute source — Unmute source\n"
        "• /muted — List muted sources\n\n"
        "<b>Admin:</b> /broadcast_text, /broadcast_media, /sources, /refetch"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.in_(BTN_ADMIN))
async def open_admin(message: Message, admin_ids: set[int]):
    if message.from_user.id not in admin_ids:
        return await message.answer("Admins only.")
    await message.answer("🛠 <b>Admin panel:</b>", reply_markup=kb_admin(), parse_mode="HTML")

@router.message(F.text.in_(BTN_BACK))
async def go_back(message: Message, storage: Storage, admin_ids: set[int]):
    user_id = message.from_user.id
    is_admin = user_id in admin_ids
    subscribed = await storage.is_subscribed(user_id)
    await message.answer("⬅️ <b>Main menu:</b>", reply_markup=kb_main(subscribed, is_admin), parse_mode="HTML")

@router.message(F.text.in_(BTN_SUB))
@router.message(Command("subscribe"))
async def do_subscribe(message: Message, storage: Storage, admin_ids: set[int]):
    await storage.set_subscription(message.from_user.id, True)
    is_admin = message.from_user.id in admin_ids
    await message.answer(
        "🔔 <b>Notifications enabled!</b>",
        reply_markup=kb_main(True, is_admin),
        parse_mode="HTML"
    )

@router.message(F.text.in_(BTN_UNSUB))
@router.message(Command("unsubscribe"))
async def do_unsubscribe(message: Message, storage: Storage, admin_ids: set[int]):
    await storage.set_subscription(message.from_user.id, False)
    is_admin = message.from_user.id in admin_ids
    await message.answer(
        "🔕 <b>Notifications disabled.</b>",
        reply_markup=kb_main(False, is_admin),
        parse_mode="HTML"
    )