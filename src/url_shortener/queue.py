import logging
from ipaddress import IPv4Address, IPv6Address
from typing import Literal, cast
from uuid import UUID

from fastapi import Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
VISIT_STREAM = "url-shortener:visits"
FAILED_STREAM = "url-shortener:visits:failed"
CONSUMER_GROUP = "visit-writers"


class VisitEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    event_id: UUID
    short_code: str = Field(pattern=r"^[0-9a-zA-Z]+$", max_length=11)
    client_ip: IPv4Address | IPv6Address
    visited_at: AwareDatetime


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


async def get_queue(request: Request) -> VisitQueue:
    return cast(VisitQueue, request.app.state.visit_queue)
