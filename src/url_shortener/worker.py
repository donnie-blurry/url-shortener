import asyncio
import logging
import signal
from contextlib import AsyncExitStack

from prometheus_client import CollectorRegistry

from url_shortener.config import Settings
from url_shortener.database import create_database
from url_shortener.metrics import serve_metrics
from url_shortener.visits.queue import create_queue
from url_shortener.visits.worker import VisitWorker


async def main() -> None:
    settings = Settings()
    registry = CollectorRegistry()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    async with AsyncExitStack() as stack:
        engine, sessions = create_database(settings)
        stack.push_async_callback(engine.dispose)
        queue = create_queue(settings, worker=True)
        stack.push_async_callback(queue.client.aclose)
        worker = VisitWorker(queue, sessions, registry=registry)
        stack.enter_context(serve_metrics(settings, registry))
        await worker.run(stop)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
