import ccxt.async_support as ccxt


def ccxt_exchange_factory(
        exchange_id: str,
        proxy: str | None = None
) -> ccxt.Exchange:
    exchange = getattr(ccxt, exchange_id)()
    exchange.httpsProxy = proxy
    exchange.options['maxRetriesOnFailure'] = 3
    exchange.options['maxRetriesOnFailureDelay'] = 1000

    return exchange
