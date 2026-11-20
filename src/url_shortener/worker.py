import asyncio
import logging
import signal

from url_shortener.config import Settings
from url_shortener.database import create_database
from url_shortener.visits.queue import create_queue
from url_shortener.visits.worker import VisitWorker


async def main() -> None:
    settings = Settings()
    engine, sessions = create_database(settings)
    queue = create_queue(settings, worker=True)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    try:
        await VisitWorker(queue, sessions).run(stop)
    finally:
        try:
            await queue.client.aclose()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
