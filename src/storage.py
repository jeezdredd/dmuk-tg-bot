import aiosqlite
import datetime
from typing import List, Tuple, Optional

class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    is_admin INTEGER DEFAULT 0,
                    subscribed_news INTEGER DEFAULT 1,
                    created_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    text TEXT,
                    source TEXT,
                    created_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ingested_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    created_at TEXT,
                    UNIQUE(source, external_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_keywords (
                    user_id INTEGER,
                    keyword TEXT,
                    created_at TEXT,
                    UNIQUE(user_id, keyword)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_muted_sources (
                    user_id INTEGER,
                    source TEXT,
                    created_at TEXT,
                    UNIQUE(user_id, source)
                )
            """)
            # Новые поля пользователя
            await self._ensure_column(db, "users", "student_id", "TEXT")
            await self._ensure_column(db, "users", "full_name", "TEXT")
            await self._ensure_column(db, "users", "profile_photo", "TEXT")
            # Новые поля в news
            await self._ensure_column(db, "news", "post_url", "TEXT")
            await self._ensure_column(db, "news", "external_url", "TEXT")
            await self._ensure_column(db, "news", "media_path", "TEXT")
            await self._ensure_column(db, "news", "source_title", "TEXT")
            await db.commit()

    async def _ensure_column(self, db: aiosqlite.Connection, table: str, column: str, col_type: str):
        async with db.execute(f"PRAGMA table_info({table})") as cur:
            cols = [row[1] for row in await cur.fetchall()]
        if column not in cols:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except Exception:
                pass

    # ---------- Users ----------
    async def add_or_update_user(self, user_id: int, is_admin: bool):
        now = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, is_admin, subscribed_news, created_at) VALUES (?, ?, 1, ?)",
                (user_id, 1 if is_admin else 0, now)
            )
            await db.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (1 if is_admin else 0, user_id))
            await db.commit()

    async def set_subscription(self, user_id: int, subscribed: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET subscribed_news = ? WHERE user_id = ?", (1 if subscribed else 0, user_id))
            await db.commit()

    async def is_subscribed(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT subscribed_news FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                return bool(row and row[0])

    async def set_student_profile(self, user_id: int, student_id: str, full_name: str, profile_photo: Optional[str] = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET student_id = ?, full_name = ?, profile_photo = ? WHERE user_id = ?",
                (student_id, full_name, profile_photo, user_id)
            )
            await db.commit()

    async def get_student_profile(self, user_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT student_id, full_name, profile_photo FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    return row
                return (None, None, None)

    async def get_all_user_ids(self, only_subscribed: bool = False) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT user_id FROM users WHERE subscribed_news = 1" if only_subscribed else "SELECT user_id FROM users"
            async with db.execute(query) as cur:
                rows = await cur.fetchall()
                return [r[0] for r in rows]

    # ---------- News ----------
    async def add_news(self, title: str, text: str, source: str,
                       post_url: Optional[str] = None, external_url: Optional[str] = None,
                       media_path: Optional[str] = None, source_title: Optional[str] = None):
        now = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO news (title, text, source, created_at, post_url, external_url, media_path, source_title) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, text, source, now, post_url, external_url, media_path, source_title)
            )
            await db.commit()

    async def add_news_if_new(self, title: str, text: str, source: str, external_id: Optional[str],
                              post_url: Optional[str] = None, external_url: Optional[str] = None,
                              media_path: Optional[str] = None, source_title: Optional[str] = None) -> bool:
        now = datetime.datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("BEGIN")
            try:
                if external_id:
                    async with db.execute(
                        "SELECT 1 FROM ingested_items WHERE source = ? AND external_id = ?",
                        (source, external_id)
                    ) as cur:
                        if await cur.fetchone():
                            await db.execute("ROLLBACK")
                            return False
                await db.execute(
                    "INSERT INTO news (title, text, source, created_at, post_url, external_url, media_path, source_title) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (title, text, source, now, post_url, external_url, media_path, source_title)
                )
                if external_id:
                    await db.execute(
                        "INSERT OR IGNORE INTO ingested_items (source, external_id, created_at) VALUES (?, ?, ?)",
                        (source, external_id, now)
                    )
                await db.commit()
                return True
            except Exception:
                await db.execute("ROLLBACK")
                raise

    async def get_latest_news(self, limit: int = 5):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, title, text, source, created_at, post_url, external_url, media_path, source_title "
                "FROM news ORDER BY id DESC LIMIT ?",
                (limit,)
            ) as cur:
                return await cur.fetchall()

    # ---------- Filters ----------
    async def add_keyword(self, user_id: int, keyword: str):
        now = datetime.datetime.utcnow().isoformat()
        kw = (keyword or "").strip().lower()
        if not kw:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO user_keywords (user_id, keyword, created_at) VALUES (?, ?, ?)",
                (user_id, kw, now)
            )
            await db.commit()

    async def remove_keyword(self, user_id: int, keyword: str):
        kw = (keyword or "").strip().lower()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_keywords WHERE user_id = ? AND keyword = ?", (user_id, kw))
            await db.commit()

    async def list_keywords(self, user_id: int) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT keyword FROM user_keywords WHERE user_id = ? ORDER BY keyword", (user_id,)) as cur:
                rows = await cur.fetchall()
                return [r[0] for r in rows]

    async def mute_source(self, user_id: int, source: str):
        now = datetime.datetime.utcnow().isoformat()
        src = (source or "").strip().lower().lstrip("@")
        if not src:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO user_muted_sources (user_id, source, created_at) VALUES (?, ?, ?)",
                (user_id, src, now)
            )
            await db.commit()

    async def unmute_source(self, user_id: int, source: str):
        src = (source or "").strip().lower().lstrip("@")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_muted_sources WHERE user_id = ? AND source = ?", (user_id, src))
            await db.commit()

    async def list_muted_sources(self, user_id: int) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT source FROM user_muted_sources WHERE user_id = ? ORDER BY source", (user_id,)) as cur:
                rows = await cur.fetchall()
                return [r[0] for r in rows]

    async def db(self):
        return await aiosqlite.connect(self.db_path)