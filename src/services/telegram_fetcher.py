import asyncio
import os
from typing import Awaitable, Callable, Iterable, Optional

from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.custom.message import Message
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl

from src.storage import Storage


def make_title_and_text(text: str, max_title_len: int = 120) -> tuple[str, str]:
    if not text:
        return "Post", ""
    first = text.strip().splitlines()[0].strip()
    title = (first[: max_title_len] + "…") if len(first) > max_title_len else first
    return title, text


def extract_external_url(msg: Message) -> Optional[str]:
    # 1) Entities
    ents = getattr(msg, "entities", None) or []
    if ents:
        for ent in ents:
            if isinstance(ent, MessageEntityTextUrl) and getattr(ent, "url", None):
                return ent.url
            if isinstance(ent, MessageEntityUrl):
                try:
                    t = msg.message or ""
                    return t[ent.offset : ent.offset + ent.length]
                except Exception:
                    pass
    # 2) WebPage preview
    wp = getattr(getattr(msg, "media", None), "webpage", None)
    if wp and getattr(wp, "url", None):
        return wp.url
    return None


class TelegramFetcher:
    """
    Telethon-based public channels parser.
    Stores post URL, first external URL and first photo (downloaded to disk).
    on_new_item signature: (title, text, source, post_url, external_url, media_path)
    """
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str,
        channels: Iterable[str],
        storage: Storage,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.channels = [c.lstrip("@") for c in channels]
        self.storage = storage

        self.client: Optional[TelegramClient] = None
        self._running = False
        self._handler_registered = False
        self._on_new_item: Optional[Callable[[str, str, str, Optional[str], Optional[str], Optional[str]], Awaitable[None]]] = None
        self._entities = []
        self._channel_titles: dict[str, str] = {}

        self.media_dir = os.path.join("data", "media")
        os.makedirs(self.media_dir, exist_ok=True)

    async def start(
        self,
        on_new_item: Optional[Callable[[str, str, str, Optional[str], Optional[str], Optional[str]], Awaitable[None]]] = None,
        backfill_per_channel: int = 5,
    ):
        if self._running:
            return
        self._on_new_item = on_new_item

        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            print("[TelegramFetcher] Session is not authorized. Run: python -m src.tools.telethon_login")
            raise RuntimeError("Telethon session is not authorized.")
        me = await self.client.get_me()
        if getattr(me, "bot", False):
            raise RuntimeError("Telethon is logged in as a bot; login with a user account.")

        self._running = True

        # Resolve and join
        self._entities = []
        for ch in self.channels:
            try:
                entity = await self.client.get_entity(ch)
                self._entities.append(entity)
                self._channel_titles[getattr(entity, "username", ch).lower()] = getattr(entity, "title", ch)
                try:
                    await self.client(JoinChannelRequest(entity))
                    print(f"[TelegramFetcher] Joined channel: {ch}")
                except Exception:
                    pass
            except RPCError as e:
                print(f"[TelegramFetcher] Failed to get channel {ch}: {e}")

        if self._entities:
            self.client.add_event_handler(self._on_new_message, events.NewMessage(chats=self._entities))
            self._handler_registered = True

        await self._backfill(backfill_per_channel)

    async def stop(self):
        self._running = False
        if self.client:
            try:
                if self._handler_registered:
                    self.client.remove_event_handler(self._on_new_message)
                await self.client.disconnect()
            finally:
                self.client = None

    async def backfill_recent(self, per_channel: int = 5):
        await self._backfill(per_channel)

    async def _backfill(self, per_channel: int):
        if not self.client:
            return
        for ch in self.channels:
            try:
                async for msg in self.client.iter_messages(ch, limit=per_channel):
                    await self._process_message(ch, msg)
                    await asyncio.sleep(0.02)
            except RPCError as e:
                print(f"[TelegramFetcher] Backfill error for {ch}: {e}")

    async def _on_new_message(self, event: events.NewMessage.Event):
        if not self._running:
            return
        msg: Message = event.message
        try:
            ch = event.chat.username if event.chat and event.chat.username else str(event.chat_id)
        except Exception:
            ch = "unknown"
        await self._process_message(ch, msg)

    async def _process_message(self, channel: str, msg: Message):
        text = (msg.text or msg.message or "").strip()

        # Accept media-only posts via WebPage title/description
        if not text:
            wp = getattr(getattr(msg, "media", None), "webpage", None)
            if wp:
                text_parts = [getattr(wp, "title", "") or "", getattr(wp, "description", "") or ""]
                text = "\n\n".join([p for p in text_parts if p]).strip()
            if not text:
                return

        title, full_text = make_title_and_text(text)
        source_username = (channel or "unknown").lstrip("@").lower()
        source_title = self._channel_titles.get(source_username, source_username)
        external_id = f"{source_username}:{msg.id}"

        post_url = f"https://t.me/{source_username}/{msg.id}" if source_username and source_username != "unknown" else None
        external_url = extract_external_url(msg)

        media_path = None
        try:
            # (a) Photo attachment
            if msg.photo:
                filename = f"{source_username}_{msg.id}.jpg"
                path = os.path.join(self.media_dir, filename)
                if not os.path.exists(path):
                    await self.client.download_media(msg, file=path)
                media_path = path
            # (b) Document that is an image
            elif msg.document and getattr(msg.document, "mime_type", "").startswith("image/"):
                name = getattr(getattr(msg, "file", None), "name", None) or f"{source_username}_{msg.id}.jpg"
                path = os.path.join(self.media_dir, name)
                if not os.path.exists(path):
                    await self.client.download_media(msg, file=path)
                media_path = path
            # (c) WebPage preview photo (for link-only posts)
            elif getattr(getattr(msg, "media", None), "webpage", None) and getattr(msg.media.webpage, "photo", None):
                # Try downloading the whole media first, then specific photo
                filename = f"{source_username}_{msg.id}_wp.jpg"
                path = os.path.join(self.media_dir, filename)
                if not os.path.exists(path):
                    try:
                        await self.client.download_media(msg.media, file=path)
                    except Exception:
                        await self.client.download_media(msg.media.webpage.photo, file=path)
                media_path = path
        except Exception as e:
            print(f"[TelegramFetcher] Failed to download media for {source_username}/{msg.id}: {e}")

        added = await self.storage.add_news_if_new(
            title, full_text, source_username, external_id,
            post_url=post_url, external_url=external_url, media_path=media_path, source_title=source_title
        )
        if added and self._on_new_item:
            try:
                await self._on_new_item(title, full_text, source_username, post_url, external_url, media_path)
            except Exception:
                pass