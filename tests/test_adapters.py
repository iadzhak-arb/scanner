from unittest import mock

import pytest

import ccxt.async_support as ccxt

from tests.mock_data import mock_id, mock_name, mock_markets, mock_orderbook
from src.core.models import ExchangeDTO, OrderbookDTO, SymbolDTO
from src.adapters.ccxt_adapter import CCXTAdapter, ExchangeError


@pytest.fixture
def mock_ccxt_exchange():
    mock_exchange = mock.create_autospec(ccxt.Exchange, instance=True)
    mock_exchange.id = mock_id
    mock_exchange.name = mock_name
    mock_exchange.load_markets.return_value = mock_markets
    mock_exchange.fetch_order_book.return_value = mock_orderbook
    return mock_exchange


@pytest.mark.asyncio
class TestCCXTAdapter:

    @property
    def symbol(self) -> SymbolDTO:
        return SymbolDTO(id='BTC/USDT', market='spot', base='BTC', quote='USDT')

    async def test_properties(self, mock_ccxt_exchange):
        adapter = CCXTAdapter(mock_ccxt_exchange)
        assert adapter.id == mock_id
        assert adapter.name == mock_name

    async def test_load_markets_success(self, mock_ccxt_exchange):
        adapter = CCXTAdapter(mock_ccxt_exchange)
        result = await adapter.load_markets()
        mock_ccxt_exchange.load_markets.assert_awaited()
        assert isinstance(result, list)
        assert all(isinstance(item, SymbolDTO) for item in result)
        result_dict = {item.id: item for item in result}
        for k in mock_markets:
            assert result_dict[k].id == k
            assert result_dict[k].market == mock_markets[k]['type']
            assert result_dict[k].base == mock_markets[k]['base']
            assert result_dict[k].quote == mock_markets[k]['quote']
            assert result_dict[k].settle == mock_markets[k]['settle']

    async def test_load_markets_fail(self, mock_ccxt_exchange):
        mock_ccxt_exchange.load_markets.side_effect = ccxt.BaseError
        adapter = CCXTAdapter(mock_ccxt_exchange)
        with pytest.raises(ExchangeError):
            result = await adapter.load_markets()
        mock_ccxt_exchange.load_markets.assert_awaited()

    async def test_fetch_orderbook_success(self, mock_ccxt_exchange):
        adapter = CCXTAdapter(mock_ccxt_exchange)
        result = await adapter.fetch_orderbook(self.symbol)
        mock_ccxt_exchange.fetch_order_book.assert_awaited_with(symbol=self.symbol.id)
        assert isinstance(result, OrderbookDTO)
        assert result.symbol == self.symbol
        assert result.exchange == ExchangeDTO(id=mock_id, name=mock_name)
        assert result.timestamp == mock_orderbook['timestamp']
        assert result.asks == mock_orderbook['asks']
        assert result.bids == mock_orderbook['bids']

    async def test_fetch_orderbook_bad_symbol(self, mock_ccxt_exchange):
        mock_ccxt_exchange.fetch_order_book.side_effect = ccxt.BadSymbol
        adapter = CCXTAdapter(mock_ccxt_exchange)
        result = await adapter.fetch_orderbook(self.symbol)
        mock_ccxt_exchange.fetch_order_book.assert_awaited_with(symbol=self.symbol.id)
        assert result is None

    async def test_fetch_orderbook_fail(self, mock_ccxt_exchange):
        mock_ccxt_exchange.fetch_order_book.side_effect = ccxt.BaseError
        adapter = CCXTAdapter(mock_ccxt_exchange)
        with pytest.raises(ExchangeError):
            result = await adapter.fetch_orderbook(self.symbol)
        mock_ccxt_exchange.fetch_order_book.assert_awaited_with(symbol=self.symbol.id)

    async def test_close_success(self, mock_ccxt_exchange):
        adapter = CCXTAdapter(mock_ccxt_exchange)
        await adapter.close()
        mock_ccxt_exchange.close.assert_awaited()

    async def test_close_fail(self, mock_ccxt_exchange):
        mock_ccxt_exchange.close.side_effect = ccxt.BaseError
        adapter = CCXTAdapter(mock_ccxt_exchange)
        await adapter.close()
        mock_ccxt_exchange.close.assert_awaited()
