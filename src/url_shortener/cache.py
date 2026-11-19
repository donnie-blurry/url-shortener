import logging
from typing import cast

from fastapi import Request
from pydantic import ValidationError
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from url_shortener.schemas import CreateLink

logger = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 3600


class MappingCache:
    def __init__(self, client: Redis) -> None:
        self.client = client

    @staticmethod
    def key(code: str) -> str:
        return f"url-shortener:mapping:{code}"

    async def get(self, code: str) -> str | None:
        try:
            value = await self.client.get(self.key(code))
            if not isinstance(value, str):
                return None
            return CreateLink(original_url=value).original_url
        except RedisError, ValidationError, UnicodeError:
            logger.warning("Mapping cache read unavailable or invalid")
            return None

    async def set(self, code: str, destination: str) -> None:
        try:
            await self.client.set(self.key(code), destination, ex=CACHE_TTL_SECONDS)
        except RedisError:
            logger.warning("Mapping cache write unavailable")

    async def delete(self, code: str) -> None:
        try:
            await self.client.delete(self.key(code))
        except RedisError:
            logger.warning("Mapping cache eviction unavailable")


def create_cache(url: str) -> MappingCache:
    return MappingCache(
        Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
            retry=Retry(NoBackoff(), 0),
        )
    )


async def get_cache(request: Request) -> MappingCache:
    return cast(MappingCache, request.app.state.mapping_cache)
