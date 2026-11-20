from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from url_shortener.main import create_app


@pytest.mark.parametrize("failure", [None, "startup", "cleanup"])
async def test_lifespan_cleans_up_acquired_resources(monkeypatch, failure):
    cleanup_order = []

    async def dispose():
        cleanup_order.append("engine")

    async def close_cache():
        cleanup_order.append("cache")

    async def close_queue():
        cleanup_order.append("queue")
        if failure == "cleanup":
            raise RuntimeError("Queue cleanup failed")

    engine = SimpleNamespace(dispose=AsyncMock(side_effect=dispose))
    factory = object()
    cache = SimpleNamespace(
        client=SimpleNamespace(aclose=AsyncMock(side_effect=close_cache))
    )
    queue = SimpleNamespace(
        client=SimpleNamespace(aclose=AsyncMock(side_effect=close_queue))
    )
    monkeypatch.setattr(
        "url_shortener.main.create_database", lambda _: (engine, factory)
    )
    monkeypatch.setattr("url_shortener.main.create_cache", lambda _: cache)
    monkeypatch.setattr(
        "url_shortener.main.create_queue",
        Mock(side_effect=RuntimeError("Queue startup failed"))
        if failure == "startup"
        else lambda _: queue,
    )
    settings = SimpleNamespace(redis_url="redis://localhost:6379/0")
    app = create_app(settings)

    async def run_lifespan():
        async with app.router.lifespan_context(app):
            assert app.state.session_factory is factory
            assert app.state.mapping_cache is cache
            assert app.state.visit_queue is queue

    if failure:
        with pytest.raises(RuntimeError, match=f"Queue {failure} failed"):
            await run_lifespan()
    else:
        await run_lifespan()

    assert cleanup_order == (
        ["cache", "engine"] if failure == "startup" else ["queue", "cache", "engine"]
    )
