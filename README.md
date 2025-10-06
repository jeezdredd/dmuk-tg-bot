# DMUK Telegram Bot Overview

This project implements a university-oriented Telegram bot built with [Aiogram 3](https://docs.aiogram.dev/).
It combines polling-based bot interactions with optional Telethon-powered channel parsing to deliver news,
schedules, and profile management features for students and administrators.

## Application Flow

- **Entry point (`src/bot.py`)** – loads environment configuration, prepares the Aiogram `Bot` and `Dispatcher`
  with in-memory FSM storage, initializes the SQLite-backed `Storage`, and wires routers from individual
  handler modules. When Telethon credentials are available it also launches `TelegramFetcher` to monitor
  configured public channels and push updates to users based on their subscriptions and keyword filters.
- **Configuration (`src/config.py`)** – reads environment variables (using `python-dotenv`) to get the bot token,
  administrator IDs, database path, Telethon API credentials, and the list of monitored channels.
- **Persistence (`src/storage.py`)** – wraps an SQLite database accessed through `aiosqlite` and provides methods
  for managing users, news entries, keyword filters, muted sources, and enriched student profiles (ID, name,
  profile photo). Helper functions ensure new columns exist when the bot starts.

## Handlers and User Experience

Handler routers in `src/handlers/` expose the conversational features:

- **`start.py`** – greets users, shows the main reply keyboard, manages subscription toggles, and exposes the
  admin panel shortcut for administrators.
- **`news.py`** – fetches the latest news posts from storage, formats them with HTML-safe helpers, and sends
  attachments or inline "Read more" buttons when links are available.
- **`filters.py`** – lets users manage keyword-based filtering and muted sources via commands or FSM-driven
  reply keyboards.
- **`schedule.py`** – demonstrates a schedule viewer with FSM state transitions for day selection and integrates
  seamlessly with the profile handler when invoked from within the schedule flow.
- **`profile.py`** – stores and displays student profile information, including optional photo uploads saved to
  `data/profile_photos`.
- **`admin.py`** – adds administrator-only controls for listing connected channels, refetching recent posts via
  Telethon, and broadcasting text or media messages to all users.

## Background Services

- **`services/telegram_fetcher.py`** – uses Telethon to backfill and watch public channels, normalizing content
  and downloading media for storage; newly ingested posts trigger notification callbacks.
- **`services/news_fetcher.py`** – contains a demo asynchronous producer that can inject placeholder news items
  when live sources are unavailable.

## Utility Helpers

- **`utils/text.py`** – provides Markdown-to-HTML sanitization and caption clipping helpers shared by handlers
  and notification routines.
