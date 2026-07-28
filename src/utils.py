import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from src.core.models import SymbolGroupDTO
from src.services.managers import MarketsData


def get_groups(markets: MarketsData) -> list[list[SymbolGroupDTO]]:
    groups = {}
    for exchange, symbols in markets:
        for symbol in symbols:
            group_key = symbol.base, symbol.settle or symbol.quote
            group = groups.setdefault(group_key, {})
            group_symbol = group.setdefault(symbol.id, {'symbol': symbol})
            group_symbol.setdefault('exchanges', []).append(exchange)

    return [
        [
            SymbolGroupDTO(**data)
            for data in group.values()
        ]
        for group in groups.values()
    ]


class Pool[T]:
    def __init__(self, *objs: T) -> None:
        self.queue: asyncio.Queue[T] = asyncio.Queue()
        self.add(*objs)

    def add(self, *objs: T) -> None:
        for obj in objs:
            self.queue.put_nowait(obj)

    @asynccontextmanager
    async def get(self, timeout: int | None = None) -> AsyncGenerator[T, None]:
        obj = await asyncio.wait_for(self.queue.get(), timeout)
        try:
            yield obj
        finally:
            await self.queue.put(obj)
