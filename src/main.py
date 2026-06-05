import asyncio
import logging
from typing import Annotated

from aio_pika import RobustQueue
from faststream import FastStream, ContextRepo, Context

from src.adapters.ccxt_adapter import CCXTAdapter
from src.factories import ccxt_exchange_factory
from src.services.managers import ExchangeManager
from src.config import settings as st
from src.broker import broker, send_groups, queue_groups, queue_orderbooks
from src.utils import Pool

app = FastStream(broker)
logger = logging.getLogger('faststream')


@app.on_startup
async def on_startup(context: ContextRepo, publish: bool = False):
    managers: list[ExchangeManager] = []
    for proxy in st.PROXIES:
        exs = [
            CCXTAdapter(ccxt_exchange_factory(ex, proxy))
            for ex in st.EXCHANGES
        ]
        m = ExchangeManager(*exs)
        managers.append(m)
    pool = Pool[ExchangeManager](*managers)

    context.set_global('publish', publish)
    context.set_global('managers', managers)
    context.set_global('pool', pool)
    logger.info(f'Publishing groups {"enabled" if publish else "disabled"}.')
    logger.info(f'Working with exchanges: {", ".join(st.EXCHANGES)}.')
    logger.info(f'Created {len(managers)} exchange managers.')


async def publish_task(pool, queue: RobustQueue):
    while True:
        try:
            await queue.declare()
            msgs = queue.declaration_result.message_count or 0
            logger.info(f'Current GROUPS messages: {msgs}.')
            if msgs <= st.MIN_LENGTH:
                logger.info('Publishing new messages.')
                await send_groups(pool)
            await asyncio.sleep(st.TIMEOUT)
        except asyncio.CancelledError:
            break


@app.after_startup
async def after_startup(
        publish: Annotated[bool, Context()],
        pool: Annotated[Pool[ExchangeManager], Context()],
):
    await broker.declare_queue(queue_orderbooks)
    queue = await broker.declare_queue(queue_groups)
    if publish:
        asyncio.create_task(publish_task(pool, queue))


@app.after_shutdown
async def after_shutdown(managers: Annotated[list[ExchangeManager], Context()]):
    await asyncio.gather(*[manager.close() for manager in managers])
