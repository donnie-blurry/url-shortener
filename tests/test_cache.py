from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError, TimeoutError

from url_shortener.cache import CACHE_TTL_SECONDS, MappingCache


@pytest.fixture
def resources():
    client = SimpleNamespace(get=AsyncMock(), set=AsyncMock(), delete=AsyncMock())
    return client, MappingCache(client)


@pytest.mark.parametrize(
    "value", [None, "not a url", "javascript:alert(1)", b"https://example.com"]
)
async def test_cache_misses_and_malformed_values_fall_back(resources, value):
    client, cache = resources
    client.get.return_value = value
    assert await cache.get("1") is None


async def test_cache_hit_preserves_original_destination(resources):
    client, cache = resources
    client.get.return_value = "https://example.com/?a=%2F"
    assert await cache.get("1") == "https://example.com/?a=%2F"


@pytest.mark.parametrize("error", [ConnectionError, TimeoutError])
async def test_cache_outage_does_not_escape(resources, error):
    client, cache = resources
    client.get.side_effect = error()
    client.set.side_effect = error()
    client.delete.side_effect = error()
    assert await cache.get("1") is None
    await cache.set("1", "https://example.com")
    await cache.delete("1")


async def test_cache_writes_have_namespace_and_ttl(resources):
    client, cache = resources
    await cache.set("1", "https://example.com")
    client.set.assert_awaited_once_with(
        "url-shortener:mapping:1", "https://example.com", ex=CACHE_TTL_SECONDS
    )
