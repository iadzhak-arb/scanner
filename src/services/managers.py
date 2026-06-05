import asyncio
from typing import Protocol

from src.core.models import ExchangeDTO, SymbolDTO, OrderbookDTO

MarketsData = list[tuple[ExchangeDTO, list[SymbolDTO]]]
OrderbooksData = list[OrderbookDTO]


class ExchangeProtocol(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    async def load_markets(self) -> dict[str, SymbolDTO]: ...

    async def fetch_orderbook(self, symbol: SymbolDTO) -> OrderbookDTO: ...

    async def close(self) -> None: ...


class ExchangeManager:

    def __init__(self, *exchanges: ExchangeProtocol) -> None:
        self.exchanges = {ex.id: ex for ex in exchanges}

    async def load_markets(self) -> MarketsData:
        responses: list[list[SymbolDTO]] = await asyncio.gather(
            *[ex.load_markets() for ex in self.exchanges.values()])
        # TODO log
        return [
            (ExchangeDTO.model_validate(exchange), market)
            for exchange, market in zip(self.exchanges.values(), responses)
        ]

    async def fetch_orderbooks(self, symbol: SymbolDTO, exchanges: list[ExchangeDTO]) -> OrderbooksData:
        responses = await asyncio.gather(*[
            self.exchanges[ex.id].fetch_orderbook(symbol)
            for ex in exchanges
        ])
        # TODO log
        return [ob for ob in responses if ob]

    async def close(self) -> None:
        await asyncio.gather(*[
            ex.close() for ex in self.exchanges.values()
        ], return_exceptions=True)
        # TODO log
