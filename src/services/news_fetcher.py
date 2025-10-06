import asyncio
import itertools
from typing import Awaitable, Callable

from src.storage import Storage


class DemoNewsFetcher:
    """
    Демо-генератор новостей.
    """
    def __init__(self, storage: Storage):
        self.storage = storage
        self._counter = itertools.count(1)
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, on_new_item: Callable[[str, str, str], 'Awaitable[None]'] | None = None, interval_sec: int = 30):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(on_new_item, interval_sec))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self, on_new_item, interval_sec: int):
        for _ in range(3):
            await self._produce_news(on_new_item)
        while self._running:
            await asyncio.sleep(interval_sec)
            await self._produce_news(on_new_item)

    async def _produce_news(self, on_new_item):
        n = next(self._counter)
        title = f"Демо-новость #{n}"
        text = f"Это демонстрационная новость #{n}. В проде здесь будет контент из Telegram/сайта университета."
        source = "demo"
        await self.storage.add_news(title, text, source)
        if on_new_item:
            # демо-новости без ссылок
            await on_new_item(title, text, source)