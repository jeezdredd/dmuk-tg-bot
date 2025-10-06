import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from config import load_config
from src.storage import Storage
from src.handlers import start as start_handlers
from src.handlers import news as news_handlers
from src.handlers import admin as admin_handlers
from src.handlers import filters as filters_handlers
from src.handlers import schedule as schedule_handlers   # NEW
from src.handlers import profile as profile_handlers     # NEW
from src.services.telegram_fetcher import TelegramFetcher
from src.utils.text import md_to_html, clip_for_caption


async def main():
    config = load_config()

    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    storage = Storage(config.db_path)
    await storage.init()

    dp["storage"] = storage
    dp["admin_ids"] = config.admin_ids
    dp["tg_channels"] = config.tg_channels

    dp.include_router(start_handlers.router)
    dp.include_router(news_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(filters_handlers.router)
    dp.include_router(schedule_handlers.router)
    dp.include_router(profile_handlers.router)

    async def user_allows(user_id: int, source: str, title: str, text: str) -> bool:
        if user_id in config.admin_ids:
            return True
        muted = set(await storage.list_muted_sources(user_id))
        if source.lower() in muted:
            return False
        kws = await storage.list_keywords(user_id)
        if not kws:
            return True
        lc = f"{title}\n{text}".lower()
        return any(kw in lc for kw in kws)

    async def notify_new_item(title: str, text: str, source: str, post_url: str | None, external_url: str | None, media_path: str | None):
        user_ids = await storage.get_all_user_ids(only_subscribed=True)
        url = post_url or external_url
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔗 Read more", url=url)]]) if url else None
        preview_tail = f"\n\n{url}" if (url and not (media_path and os.path.exists(media_path))) else ""
        body = f'🆕 <a href="https://t.me/{source}">{source}</a>\n\n{md_to_html(text or "")}{preview_tail}'

        for uid in user_ids:
            try:
                if not await user_allows(uid, source, title, text):
                    continue
                if media_path and os.path.exists(media_path):
                    await bot.send_photo(uid, FSInputFile(media_path), caption=clip_for_caption(body), reply_markup=kb)
                else:
                    await bot.send_message(uid, body, reply_markup=kb, disable_web_page_preview=False)
                await asyncio.sleep(0.03)
            except Exception:
                pass

    telegram_fetcher: TelegramFetcher | None = None
    if config.telegram_api_id and config.telegram_api_hash and config.tg_channels:
        telegram_fetcher = TelegramFetcher(
            api_id=config.telegram_api_id,
            api_hash=config.telegram_api_hash,
            session_name=config.telegram_session_name,
            channels=config.tg_channels,
            storage=storage,
        )
        await telegram_fetcher.start(on_new_item=notify_new_item, backfill_per_channel=5)
        dp["telegram_fetcher"] = telegram_fetcher
        print(f"Telegram parser started for channels: {', '.join(config.tg_channels)}")
    else:
        print("Telethon not configured; parsing disabled.")

    print("Bot started. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    finally:
        if telegram_fetcher:
            await telegram_fetcher.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())