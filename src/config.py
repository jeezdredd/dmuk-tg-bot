from dataclasses import dataclass
from dotenv import load_dotenv
import os

@dataclass
class Config:
    bot_token: str
    admin_ids: set[int]
    db_path: str
    telegram_api_id: int | None
    telegram_api_hash: str | None
    telegram_session_name: str
    tg_channels: list[str]


def load_config() -> Config:
    load_dotenv()

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in .env")

    raw_admins = os.getenv("ADMIN_IDS", "").replace(" ", "")
    admin_ids: set[int] = set()
    if raw_admins:
        for part in raw_admins.split(","):
            if part:
                try:
                    admin_ids.add(int(part))
                except ValueError:
                    pass

    db_path = os.getenv("DB_PATH", "bot.db")

    # Telethon config (optional)
    api_id_env = os.getenv("TELEGRAM_API_ID")
    telegram_api_id = int(api_id_env) if api_id_env and api_id_env.isdigit() else None
    telegram_api_hash = os.getenv("TELEGRAM_API_HASH") or None
    telegram_session_name = os.getenv("TELEGRAM_SESSION_NAME", "telegram")

    channels_raw = os.getenv("TG_CHANNELS", "")
    tg_channels = [c.strip().lstrip("@") for c in channels_raw.split(",") if c.strip()]

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        db_path=db_path,
        telegram_api_id=telegram_api_id,
        telegram_api_hash=telegram_api_hash,
        telegram_session_name=telegram_session_name,
        tg_channels=tg_channels,
    )