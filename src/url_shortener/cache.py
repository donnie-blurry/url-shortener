import logging

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from url_shortener.config import Settings
from url_shortener.links.schemas import CreateLink

logger = logging.getLogger(__name__)


class MappingCache:
    def __init__(self, client: Redis, *, key_prefix: str, ttl_seconds: int) -> None:
        self.client = client
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds

    def key(self, code: str) -> str:
        return f"{self.key_prefix}:mapping:{code}"

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
            await self.client.set(self.key(code), destination, ex=self.ttl_seconds)
        except RedisError:
            logger.warning("Mapping cache write unavailable")

    async def delete(self, code: str) -> None:
        try:
            await self.client.delete(self.key(code))
        except RedisError:
            logger.warning("Mapping cache eviction unavailable")


def create_cache(settings: Settings) -> MappingCache:
    return MappingCache(
        Redis.from_url(
            str(settings.redis_url),
            decode_responses=True,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_cache_timeout_seconds,
            retry=Retry(NoBackoff(), 0),
        ),
        key_prefix=settings.redis_key_prefix,
        ttl_seconds=settings.cache_ttl_seconds,
    )
