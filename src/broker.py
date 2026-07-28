import asyncio
import logging
from typing import Annotated

from faststream import Context, Logger
from faststream.exceptions import StopApplication
from faststream.rabbit import RabbitBroker, Channel, RabbitQueue


from src.core.exceptions import ExchangeError
from src.core.models import SymbolGroupDTO
from src.services.managers import ExchangeManager
from src.config import settings as st
from src.utils import Pool, get_groups

channel = Channel(prefetch_count=len(st.PROXIES))
broker = RabbitBroker(st.rmq_url, default_channel=channel)

queue_groups = RabbitQueue(st.QUEUE_GROUPS, durable=True)
queue_orderbooks = RabbitQueue(st.QUEUE_ORDERBOOKS, durable=True)

publisher_groups = broker.publisher(queue_groups)
publisher_orderbooks = broker.publisher(queue_orderbooks)

logger = logging.getLogger('faststream')




async def send_groups(pool: Pool[ExchangeManager]):
    async with pool.get() as manager:
        try:
            markets = await manager.load_markets()
            groups = get_groups(markets)
            for group in groups:
                await publisher_groups.publish(group)
            logger.info(f'Send {len(groups)} groups.')
        except ExchangeError as e:
            logger.exception(e)
            raise StopApplication()


@broker.subscriber(queue_groups)
async def handle_groups(
        groups: list[SymbolGroupDTO],
        pool: Annotated[Pool[ExchangeManager], Context()],
        log: Logger
):
    async with pool.get() as manager:
        try:
            orderbooks = await asyncio.gather(*[
                manager.fetch_orderbooks(group.symbol, group.exchanges)
                for group in groups
            ])
            orderbooks = [item for sublist in orderbooks for item in sublist]
            await publisher_orderbooks.publish(orderbooks)
            log.info(f'Send {len(orderbooks)} orderbooks.')
        except ExchangeError as e:
            log.exception(e)
            raise StopApplication()
        except asyncio.CancelledError:
            pass
