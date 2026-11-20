from datetime import UTC, datetime
from ipaddress import ip_address
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from redis.exceptions import ConnectionError, TimeoutError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.api.dependencies import get_cache, get_queue, get_session
from url_shortener.cache import MappingCache
from url_shortener.config import Settings
from url_shortener.links.models import ShortLink
from url_shortener.main import create_app
from url_shortener.visits.queue import VisitQueue


@pytest.fixture
def resources():
    events = []
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=1)
    session.flush = AsyncMock(side_effect=lambda: events.append("flush"))
    cache = MagicMock(spec=MappingCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    queue = MagicMock(spec=VisitQueue)
    queue.publish = AsyncMock()
    state = SimpleNamespace(
        session=session, cache=cache, queue=queue, owner=uuid4(), events=events
    )

    class Transaction:
        async def __aenter__(self):
            events.append("begin")

        async def __aexit__(self, kind, value, traceback):
            events.append("rollback" if kind else "commit")
            return False

    session.begin.side_effect = Transaction
    state.app = create_app()
    state.app.state.settings = Settings(
        database_url="postgresql+psycopg://localhost/shortener",
        redis_url="redis://localhost/0",
        _env_file=None,
    )

    async def override_session():
        yield session

    async def override_cache():
        return cache

    async def override_queue():
        return state.queue

    state.app.dependency_overrides[get_session] = override_session
    state.app.dependency_overrides[get_cache] = override_cache
    state.app.dependency_overrides[get_queue] = override_queue
    return state


def result(value):
    return SimpleNamespace(scalar_one_or_none=lambda: value)


def link(owner):
    return ShortLink(
        short_code="1",
        original_url="https://example.com/page",
        owner_id=owner,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        visit_count=42,
    )


@pytest.fixture
async def client(resources):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=resources.app, client=("127.0.0.1", 1234)),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        yield client


async def test_create_returns_committed_independent_link(client, resources):
    response = await client.post(
        "/shorten",
        json={"original_url": "https://example.com/page"},
        headers={"X-User-ID": str(resources.owner)},
    )
    assert response.status_code == 201
    assert set(response.json()) == {"short_code", "original_url", "created_at"}
    assert response.json()["created_at"].endswith("Z")
    assert resources.session.add.call_args.args[0].owner_id == resources.owner
    assert resources.events == ["begin", "flush", "commit"]
    resources.queue.publish.assert_not_awaited()


async def test_cache_miss_publishes_visit_after_lookup_and_releases_session(
    client, resources
):
    resources.session.execute.return_value = result("https://example.com/page")

    async def published(event):
        assert resources.events == ["begin", "commit"]
        assert event.client_ip == ip_address("127.0.0.1")
        assert event.short_code == "1"
        assert event.visited_at.tzinfo is not None

    resources.queue.publish.side_effect = published
    response = await client.get("/1", headers={"X-Forwarded-For": "192.0.2.1"})
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page"
    assert response.headers["cache-control"] == "no-store"
    resources.queue.publish.assert_awaited_once()
    resources.session.add.assert_not_called()
    resources.session.flush.assert_not_awaited()
    resources.cache.set.assert_awaited_once_with("1", "https://example.com/page")


async def test_cache_hit_does_not_access_postgres_even_during_outage(client, resources):
    resources.cache.get.return_value = "https://example.com/page"
    resources.session.execute.side_effect = SQLAlchemyError("unavailable")
    assert (await client.get("/1")).status_code == 302
    resources.session.execute.assert_not_awaited()
    resources.session.begin.assert_not_called()
    resources.queue.publish.assert_awaited_once()


async def test_repeated_ip_requests_publish_distinct_events(client, resources):
    resources.cache.get.return_value = "https://example.com/page"
    assert (await client.get("/1")).status_code == 302
    assert (await client.get("/1")).status_code == 302
    first, second = [call.args[0] for call in resources.queue.publish.await_args_list]
    assert first.event_id != second.event_id
    assert first.client_ip == second.client_ip
    resources.session.add.assert_not_called()


async def test_unknown_code_does_not_publish(client, resources):
    resources.session.execute.return_value = result(None)
    assert (await client.get("/unknown")).status_code == 404
    resources.queue.publish.assert_not_awaited()
    resources.cache.set.assert_not_awaited()
    resources.session.add.assert_not_called()


async def test_database_failure_on_cache_miss_is_still_503(client, resources):
    resources.session.execute.side_effect = SQLAlchemyError("unavailable")
    assert (await client.get("/1")).status_code == 503
    resources.queue.publish.assert_not_awaited()


@pytest.mark.parametrize("error", [ConnectionError, TimeoutError])
async def test_publish_failure_still_redirects(client, resources, error):
    resources.cache.get.return_value = "https://example.com/page"
    redis = SimpleNamespace(xadd=AsyncMock(side_effect=error("unavailable")))
    resources.queue = VisitQueue(redis, stream="test:visits")
    response = await client.get("/1")
    assert response.status_code == 302
    redis.xadd.assert_awaited_once()
    assert redis.xadd.await_args.args[0] == "test:visits"
    resources.session.add.assert_not_called()


async def test_statistics_report_processed_count_without_queue_or_cache(
    client, resources
):
    resources.cache.get.return_value = "https://example.com/page"
    assert (await client.get("/1")).status_code == 302
    stored = link(resources.owner)
    stored.visit_count = 0
    resources.session.execute.return_value = result(stored)
    stats = await client.get("/stats/1", headers={"X-User-ID": str(resources.owner)})
    assert stats.status_code == 200
    assert stats.json()["visit_count"] == 0
    assert stats.headers["cache-control"] == "no-store"
    assert resources.queue.publish.await_count == 1
    stored.visit_count = 1
    stats = await client.get("/stats/1", headers={"X-User-ID": str(resources.owner)})
    assert stats.json()["visit_count"] == 1


async def test_stats_response_fields_and_ownership(client, resources):
    resources.session.execute.return_value = result(link(resources.owner))
    response = await client.get("/stats/1", headers={"X-User-ID": str(resources.owner)})
    assert response.json() == {
        "short_code": "1",
        "original_url": "https://example.com/page",
        "created_at": "2026-01-01T00:00:00Z",
        "visit_count": 42,
    }
    response = await client.get("/stats/1", headers={"X-User-ID": str(uuid4())})
    assert response.status_code == 403
    assert "visit_count" not in response.json()
    resources.queue.publish.assert_not_awaited()


async def test_unknown_stats_are_404(client, resources):
    resources.session.execute.return_value = result(None)
    response = await client.get(
        "/stats/unknown", headers={"X-User-ID": str(resources.owner)}
    )
    assert response.status_code == 404


@pytest.mark.parametrize("path", ["/health", "/stats/1"])
async def test_database_failure_returns_503(client, resources, path):
    resources.session.scalar.side_effect = SQLAlchemyError("unavailable")
    resources.session.execute.side_effect = SQLAlchemyError("unavailable")
    response = await client.get(path, headers={"X-User-ID": str(resources.owner)})
    assert response.status_code == 503


async def test_health_does_not_publish(client, resources):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
    resources.session.scalar.assert_awaited_once()
    resources.queue.publish.assert_not_awaited()


@pytest.mark.parametrize("path", ["/shorten", "/stats/1"])
async def test_management_endpoints_require_uuid_header(client, path):
    response = await client.request(
        "POST" if path == "/shorten" else "GET",
        path,
        json={"original_url": "https://example.com"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("peer", [None, ("invalid-ip", 1234)])
async def test_missing_or_invalid_client_ip_does_not_block_redirect(resources, peer):
    resources.cache.get.return_value = "https://example.com/page"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=resources.app, client=peer),
        base_url="http://test",
    ) as client:
        assert (await client.get("/1")).status_code == 302
    resources.queue.publish.assert_not_awaited()
