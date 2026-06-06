from unittest import mock
from unittest.mock import MagicMock

import pytest
from deepdiff import DeepDiff

from core.models import SymbolDTO
from adapters.ccxt_adapter import ExchangeError
from services.managers import ExchangeManager, ExchangeProtocol
from core.models import ExchangeDTO


@pytest.mark.asyncio
class TestExchangeManager:

    @staticmethod
    def mock_exchanges_factory():
        exchanges = []
        for i in range(3):
            exchange = mock.MagicMock(spec=ExchangeProtocol)
            exchange.id = f'exchange{i}'
            exchange.name = f'Exchange #{i}'
            exchanges.append(exchange)
        return exchanges

    async def test_load_markets_success(self):
        mock_exchanges = self.mock_exchanges_factory()
        mock_manager = ExchangeManager(*mock_exchanges)
        result = await mock_manager.load_markets()
        for exchange in mock_exchanges:
            exchange.load_markets.assert_awaited()
        expected = [(ExchangeDTO.model_validate(e), e.load_markets.return_value) for e in mock_exchanges]
        diff = DeepDiff(result, expected, ignore_order=True)
        assert diff == {}, 'Результат не соответствует ожидаемому.'

    async def test_load_markets_fail(self):
        mock_exchanges = self.mock_exchanges_factory()
        mock_exchanges[0].load_markets.side_effect = ExchangeError
        mock_manager = ExchangeManager(*mock_exchanges)
        with pytest.raises(ExchangeError):
            await mock_manager.load_markets()

    async def test_fetch_orderbooks(self):
        mock_exchanges = self.mock_exchanges_factory()
        mock_manager = ExchangeManager(*mock_exchanges)
        mock_symbol = MagicMock(spec=SymbolDTO)
        result = await mock_manager.fetch_orderbooks(
            mock_symbol,
            [ExchangeDTO.model_validate(e) for e in mock_exchanges]
        )
        expected = [e.fetch_orderbook.return_value for e in mock_exchanges]
        diff = DeepDiff(result, expected, ignore_order=True)
        assert diff == {}, 'Результат не соответствует ожидаемому.'

    async def test_fetch_orderbooks_empty(self):
        mock_exchanges = self.mock_exchanges_factory()
        mock_exchanges[0].fetch_orderbook.return_value = None
        mock_manager = ExchangeManager(*mock_exchanges)
        mock_symbol = MagicMock(spec=SymbolDTO)
        result = await mock_manager.fetch_orderbooks(
            mock_symbol,
            [ExchangeDTO.model_validate(e) for e in mock_exchanges]
        )
        expected = [e.fetch_orderbook.return_value for e in mock_exchanges if e.fetch_orderbook.return_value]
        diff = DeepDiff(result, expected, ignore_order=True)
        assert diff == {}, 'Результат не соответствует ожидаемому.'

    async def test_fetch_orderbooks_fail(self):
        mock_exchanges = self.mock_exchanges_factory()
        mock_exchanges[0].fetch_orderbook.side_effect = ExchangeError
        mock_manager = ExchangeManager(*mock_exchanges)
        mock_symbol = MagicMock(spec=SymbolDTO)
        with pytest.raises(ExchangeError):
            result = await mock_manager.fetch_orderbooks(
                mock_symbol,
                [ExchangeDTO.model_validate(e) for e in mock_exchanges]
            )

    async def test_close_success(self):
        mock_exchanges = self.mock_exchanges_factory()
        mock_manager = ExchangeManager(*mock_exchanges)
        await mock_manager.close()

    async def test_close_fail(self):
        mock_exchanges = self.mock_exchanges_factory()
        mock_exchanges[0].close.side_effect = ExchangeError
        mock_manager = ExchangeManager(*mock_exchanges)
        await mock_manager.close()
