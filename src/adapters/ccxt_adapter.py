import datetime as dt

import ccxt.async_support as ccxt

from src.config import settings as st
from src.core.models import ExchangeDTO, SymbolDTO, OrderbookDTO
from src.core.exceptions import ExchangeError


class CCXTAdapter:
    def __init__(self, exchange: ccxt.Exchange) -> None:
        self._exchange = exchange

    @property
    def id(self) -> str:
        return self._exchange.id

    @property
    def name(self) -> str:
        return self._exchange.name

    async def load_markets(self) -> list[SymbolDTO]:
        try:
            response = await self._exchange.load_markets(reload=True)
        except ccxt.BaseError as e:
            raise ExchangeError(e)
        return [
            SymbolDTO(
                id=v['symbol'],
                market=v['type'],
                base=v['base'],
                quote=v['quote'],
                settle=v['settle']
            )
            for v in response.values()
            if v['type'] in st.CCXT_MARKETS
        ]

    async def fetch_orderbook(self, symbol: SymbolDTO) -> OrderbookDTO | None:
        try:
            response = await self._exchange.fetch_order_book(symbol=symbol.id)
        except ccxt.BadSymbol as e:
            # TODO log warning
            return None
        except ccxt.BaseError as e:
            raise ExchangeError(e)

        if not isinstance(response['timestamp'], float | int):
            response['timestamp'] = dt.datetime.now()
        else:
            response['timestamp'] = response['timestamp'] / 1000

        return OrderbookDTO(
            symbol=symbol,
            exchange=ExchangeDTO(id=self._exchange.id, name=self._exchange.name),
            timestamp=response['timestamp'],
            asks=response['asks'],
            bids=response['bids']
        )

    async def close(self) -> None:
        try:
            await self._exchange.close()
        except ccxt.BaseError as e:
            # TODO log warning
            pass
