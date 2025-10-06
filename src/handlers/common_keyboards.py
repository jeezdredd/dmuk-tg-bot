from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def kb_main(is_subscribed: bool, is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📰 News")],
        [KeyboardButton(text="🔔 Subscribe") if not is_subscribed else KeyboardButton(text="🔕 Unsubscribe")],
        [KeyboardButton(text="⚙️ Filters")],
        [KeyboardButton(text="📅 Schedule"), KeyboardButton(text="👤 Profile")],
        [KeyboardButton(text="❓ Help")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🛠 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)