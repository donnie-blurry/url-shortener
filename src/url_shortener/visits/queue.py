import logging

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from url_shortener.config import Settings
from url_shortener.visits.events import VisitEvent

logger = logging.getLogger(__name__)
CONSUMER_GROUP = "visit-writers"


class VisitQueue:
    def __init__(self, client: Redis, *, stream: str) -> None:
        self.client = client
        self.stream = stream
        self.failed_stream = f"{stream}:failed"

    async def publish(self, event: VisitEvent) -> None:
        try:
            await self.client.xadd(self.stream, {"payload": event.model_dump_json()})
        except RedisError:
            logger.warning("Visit publish failed; redirect analytics may be missing")


def create_queue(settings: Settings, *, worker: bool = False) -> VisitQueue:
    return VisitQueue(
        Redis.from_url(
            str(settings.redis_url),
            decode_responses=False,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=(
                settings.redis_worker_timeout_seconds
                if worker
                else settings.redis_publish_timeout_seconds
            ),
            retry=Retry(NoBackoff(), 0),
        ),
        stream=f"{settings.redis_key_prefix}:visits",
    )
