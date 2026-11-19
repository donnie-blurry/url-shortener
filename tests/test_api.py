from datetime import UTC, datetime
from ipaddress import ip_address
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.cache import MappingCache, get_cache
from url_shortener.database import get_session
from url_shortener.main import create_app
from url_shortener.models import ShortLink, Visit


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
    cache.delete = AsyncMock()
    state = SimpleNamespace(
        session=session, cache=cache, owner=uuid4(), events=events, fail_commit=False
    )

    class Transaction:
        async def __aenter__(self):
            events.append("begin")

        async def __aexit__(self, kind, value, traceback):
            if kind:
                events.append("rollback")
            elif state.fail_commit:
                events.append("commit_failed")
                raise SQLAlchemyError("commit failed")
            else:
                events.append("commit")
            return False

    session.begin.side_effect = Transaction
    state.app = create_app()

    async def override_session():
        yield session

    async def override_cache():
        return cache

    state.app.dependency_overrides[get_session] = override_session
    state.app.dependency_overrides[get_cache] = override_cache
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


async def test_create_returns_201_with_committed_mapping(client, resources):
    response = await client.post(
        "/shorten",
        json={"original_url": "https://example.com/page"},
        headers={"X-User-ID": str(resources.owner)},
    )
    assert response.status_code == 201
    assert set(response.json()) == {"short_code", "original_url", "created_at"}
    assert response.json()["original_url"] == "https://example.com/page"
    assert response.json()["created_at"].endswith("Z")
    assert resources.session.add.call_args.args[0].owner_id == resources.owner
    assert resources.events == ["begin", "flush", "commit"]
    resources.cache.get.assert_not_awaited()


async def test_redirect_records_before_response_and_uses_direct_ip(client, resources):
    resources.session.execute.side_effect = [
        result("https://example.com/page"),
        result("1"),
    ]
    response = await client.get("/1", headers={"X-Forwarded-For": "192.0.2.1"})
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page"
    assert response.headers["cache-control"] == "no-store"
    assert resources.events == ["begin", "flush", "commit"]
    visit = resources.session.add.call_args.args[0]
    assert isinstance(visit, Visit)
    assert visit.client_ip == ip_address("127.0.0.1")
    resources.cache.set.assert_awaited_once_with("1", "https://example.com/page")


async def test_repeated_ip_visits_are_recorded_independently(client, resources):
    resources.cache.get.return_value = "https://example.com/page"
    resources.session.execute.return_value = result("1")
    assert (await client.get("/1")).status_code == 302
    assert (await client.get("/1")).status_code == 302
    assert resources.session.add.call_count == 2
    assert resources.events.count("commit") == 2


async def test_unknown_code_is_not_counted(client, resources):
    resources.session.execute.return_value = result(None)
    response = await client.get("/unknown")
    assert response.status_code == 404
    resources.session.add.assert_not_called()
    resources.session.flush.assert_not_awaited()
    resources.cache.set.assert_not_awaited()
    assert resources.events == ["begin", "rollback"]


async def test_cached_mapping_without_database_row_does_not_redirect(client, resources):
    resources.cache.get.return_value = "https://example.com"
    resources.session.execute.return_value = result(None)
    assert (await client.get("/1")).status_code == 404
    resources.cache.delete.assert_awaited_once_with("1")
    resources.session.add.assert_not_called()


@pytest.mark.parametrize("failure", ["update", "insert", "commit"])
async def test_recording_failure_never_redirects(client, resources, failure):
    resources.cache.get.return_value = "https://example.com"
    resources.session.execute.return_value = result("1")
    if failure == "update":
        resources.session.execute.side_effect = SQLAlchemyError("update failed")
    elif failure == "insert":
        resources.session.flush.side_effect = SQLAlchemyError("insert failed")
    else:
        resources.fail_commit = True
    response = await client.get("/1")
    assert response.status_code == 503
    assert "location" not in response.headers
    assert "commit" not in resources.events
    resources.cache.set.assert_not_awaited()


async def test_owner_reads_current_stats_without_cache(client, resources):
    resources.session.execute.return_value = result(link(resources.owner))
    response = await client.get("/stats/1", headers={"X-User-ID": str(resources.owner)})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "short_code": "1",
        "original_url": "https://example.com/page",
        "created_at": "2026-01-01T00:00:00Z",
        "visit_count": 42,
    }
    resources.cache.get.assert_not_awaited()
    resources.session.add.assert_not_called()


async def test_new_link_stats_are_zero(client, resources):
    stored = link(resources.owner)
    stored.visit_count = 0
    resources.session.execute.return_value = result(stored)
    response = await client.get("/stats/1", headers={"X-User-ID": str(resources.owner)})
    assert response.json()["visit_count"] == 0


async def test_other_owner_is_forbidden(client, resources):
    resources.session.execute.return_value = result(link(uuid4()))
    response = await client.get("/stats/1", headers={"X-User-ID": str(resources.owner)})
    assert response.status_code == 403
    assert "visit_count" not in response.json()


async def test_missing_link_stats_are_404(client, resources):
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


async def test_health_does_not_record_visits(client, resources):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
    resources.session.scalar.assert_awaited_once()
    resources.session.add.assert_not_called()
    resources.cache.get.assert_not_awaited()


@pytest.mark.parametrize("path", ["/shorten", "/stats/1"])
async def test_management_endpoints_require_uuid_header(client, path):
    response = await client.request(
        "POST" if path == "/shorten" else "GET",
        path,
        json={"original_url": "https://example.com"},
    )
    assert response.status_code == 422


async def test_redirect_missing_client_ip_returns_503(resources):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=resources.app, client=None),
        base_url="http://test",
    ) as client:
        assert (await client.get("/1")).status_code == 503
    resources.session.add.assert_not_called()
