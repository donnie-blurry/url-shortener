import logging

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from url_shortener.visits.events import VisitEvent

logger = logging.getLogger(__name__)
VISIT_STREAM = "url-shortener:visits"
FAILED_STREAM = "url-shortener:visits:failed"
CONSUMER_GROUP = "visit-writers"


class VisitQueue:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def publish(self, event: VisitEvent) -> None:
        try:
            await self.client.xadd(VISIT_STREAM, {"payload": event.model_dump_json()})
        except RedisError:
            logger.warning("Visit publish failed; redirect analytics may be missing")


def create_queue(url: str, read_timeout: float = 0.2) -> VisitQueue:
    return VisitQueue(
        Redis.from_url(
            url,
            decode_responses=False,
            socket_connect_timeout=0.2,
            socket_timeout=read_timeout,
            retry=Retry(NoBackoff(), 0),
        )
    )
