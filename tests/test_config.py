from url_shortener.cache import create_cache
from url_shortener.config import Settings
from url_shortener.visits.queue import create_queue


async def test_settings_apply_redis_overrides_to_api_and_worker(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("REDIS_KEY_PREFIX=local\nCACHE_TTL_SECONDS=120\n")
    monkeypatch.setenv("REDIS_KEY_PREFIX", "staging")
    monkeypatch.delenv("CACHE_TTL_SECONDS", raising=False)
    monkeypatch.setenv("REDIS_CACHE_TIMEOUT_SECONDS", "0.3")
    monkeypatch.setenv("REDIS_PUBLISH_TIMEOUT_SECONDS", "0.4")
    monkeypatch.setenv("REDIS_WORKER_TIMEOUT_SECONDS", "6")
    monkeypatch.setenv("MAX_CODE_ATTEMPTS", "3")
    settings = Settings(
        database_url="postgresql+psycopg://localhost/shortener",
        redis_url="redis://localhost/0",
        _env_file=env_file,
    )

    cache = create_cache(settings)
    publisher = create_queue(settings)
    worker_queue = create_queue(settings, worker=True)
    try:
        assert settings.max_code_attempts == 3
        assert cache.key("1") == "staging:mapping:1"
        assert cache.ttl_seconds == 120
        assert publisher.stream == worker_queue.stream == "staging:visits"
        assert worker_queue.failed_stream == "staging:visits:failed"
        assert cache.client.connection_pool.connection_kwargs["socket_timeout"] == 0.3
        assert (
            publisher.client.connection_pool.connection_kwargs["socket_timeout"] == 0.4
        )
        assert (
            worker_queue.client.connection_pool.connection_kwargs["socket_timeout"] == 6
        )
    finally:
        await cache.client.aclose()
        await publisher.client.aclose()
        await worker_queue.client.aclose()
