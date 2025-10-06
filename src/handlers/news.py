import os
import html
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command

from src.storage import Storage
from src.utils.text import md_to_html, clip_for_caption

router = Router(name="news")


def build_read_more_kb(post_url: str | None, external_url: str | None) -> InlineKeyboardMarkup | None:
    url = post_url or external_url
    if not url:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔗 Read more", url=url)]])


def source_line(source_username: str, source_title: str | None) -> str:
    username = (source_username or "").strip().lstrip("@")
    label = (source_title or username or "").strip()
    if not label:
        label = "Unknown"
    label_safe = html.escape(label, quote=False)
    if not username:
        return f"📰 {label_safe}"
    return f'📰 <a href="https://t.me/{username}">{label_safe}</a>'


@router.message(F.text.in_({"📰 News", "Новости"}))
@router.message(Command("news"))
async def cmd_news(message: Message, storage: Storage):
    rows = await storage.get_latest_news(limit=5)
    if not rows:
        await message.answer("No news yet. Please check later!")
        return

    for row in rows:
        # id, title, text, source, created_at, post_url, external_url, media_path, source_title
        _id, title, text, source_username, *rest = row
        post_url = rest[1] if len(rest) >= 2 else None
        external_url = rest[2] if len(rest) >= 3 else None
        media_path = rest[3] if len(rest) >= 4 else None
        source_title = rest[4] if len(rest) >= 5 else None

        header = source_line(source_username, source_title)
        body_html = md_to_html(text or "")
        kb = build_read_more_kb(post_url, external_url)

        add_preview_url = (external_url or post_url) if not media_path else None
        preview_tail = f"\n\n{add_preview_url}" if add_preview_url else ""

        caption = f"{header}\n\n{body_html}{preview_tail}"

        if media_path and os.path.exists(media_path):
            await message.answer_photo(photo=FSInputFile(media_path), caption=clip_for_caption(caption), reply_markup=kb)
        else:
            await message.answer(caption, reply_markup=kb, disable_web_page_preview=False)