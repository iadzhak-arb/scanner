import pytest

from src.factories import ccxt_exchange_factory


class TestCcxtExchangeFactory:

    @pytest.mark.parametrize('exchange_id, proxy', (
            ('bybit', None),
            ('kucoin', 'http://user:pass@localhost:8080')
    ), ids=('no_proxy', 'with_proxy'))
    def test_valid_id(self, exchange_id, proxy):
        exchange = ccxt_exchange_factory(exchange_id, proxy)
        assert exchange.id == exchange_id
        assert exchange.httpsProxy == proxy
        exchange.enableRateLimit = True, \
            'RateLimit должен быть включён по умолчанию'
        assert exchange.options['maxRetriesOnFailure'] == 3, \
            'Максимальное количество попыток должно равняться 3 по умолчанию'
        assert exchange.options['maxRetriesOnFailureDelay'] == 1000, \
            'Интервал между повторными запросами должен равняться 1s по умолчанию'

    def test_invalid_id(self):
        exchange_id = 'invalid'
        with pytest.raises(AttributeError):
            exchange = ccxt_exchange_factory(exchange_id)
