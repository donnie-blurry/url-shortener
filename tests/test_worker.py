import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from prometheus_client import CollectorRegistry
from redis.exceptions import ConnectionError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from url_shortener.visits.events import VisitEvent
from url_shortener.visits.queue import CONSUMER_GROUP, VisitQueue
from url_shortener.visits.worker import VisitWorker


@pytest.fixture
def resources():
    client = MagicMock()
    queue = VisitQueue(client, stream="test:visits")
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    transaction = MagicMock(
        __aenter__=AsyncMock(), __aexit__=AsyncMock(return_value=False)
    )
    session.begin.return_value = transaction
    event_id = uuid4()
    session.execute = AsyncMock(
        return_value=SimpleNamespace(scalar_one_or_none=lambda: event_id)
    )
    sessions = MagicMock(return_value=session)
    metrics = CollectorRegistry()
    worker = VisitWorker(queue, sessions, registry=metrics)
    worker.acknowledge = AsyncMock()
    worker.quarantine = AsyncMock()
    event = VisitEvent(
        event_id=event_id,
        short_code="1",
        client_ip="192.0.2.1",
        visited_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return SimpleNamespace(
        client=client,
        queue=queue,
        session=session,
        worker=worker,
        metrics=metrics,
        transaction=transaction,
        event=event,
        fields={b"payload": event.model_dump_json().encode()},
    )


async def test_worker_commits_visit_and_count_before_ack(resources):
    r = resources

    async def acknowledge(message_id):
        r.transaction.__aexit__.assert_awaited_once_with(None, None, None)

    r.worker.acknowledge.side_effect = acknowledge
    await r.worker.process(b"1-0", r.fields)
    assert r.session.execute.await_count == 2
    statement = r.session.execute.await_args_list[0].args[0].compile()
    assert str(statement).endswith("RETURNING visits.event_id")
    values = statement.params
    assert values["event_id"] == r.event.event_id
    assert values["visited_at"] == r.event.visited_at
    assert values["short_code"] == "1"
    r.worker.acknowledge.assert_awaited_once_with(b"1-0")


async def test_replayed_event_does_not_increment_again(resources):
    r = resources
    r.session.execute.return_value.scalar_one_or_none = lambda: None
    assert await r.worker.process(b"2-0", r.fields) == "acknowledged"
    assert r.session.execute.await_count == 1
    r.worker.acknowledge.assert_awaited_once()


@pytest.mark.parametrize("failure", ["insert", "counter", "commit"])
async def test_database_failure_leaves_event_unacknowledged(resources, failure):
    r = resources
    error = SQLAlchemyError("failed")
    if failure == "insert":
        r.session.execute.side_effect = error
    elif failure == "counter":
        r.session.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: 1),
            error,
        ]
    else:
        r.transaction.__aexit__.side_effect = error
    with pytest.raises(SQLAlchemyError):
        await r.worker.process(b"1-0", r.fields)
    r.worker.acknowledge.assert_not_awaited()
    r.worker.quarantine.assert_not_awaited()
    if failure != "commit":
        assert r.transaction.__aexit__.await_args.args[0] is SQLAlchemyError


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {b"payload": b"not-json"},
        {b"payload": b"\xff"},
        {b"payload": b'{"version":2}'},
    ],
)
async def test_malformed_events_are_quarantined(resources, fields):
    assert await resources.worker.process(b"1-0", fields) == "quarantined"
    resources.worker.quarantine.assert_awaited_once_with(
        b"1-0", fields, "Invalid visit event"
    )
    resources.session.execute.assert_not_awaited()


async def test_missing_mapping_is_quarantined(resources):
    r = resources
    original = Exception("foreign key")
    original.sqlstate = "23503"
    original.diag = SimpleNamespace(constraint_name="fk_visits_short_code_short_links")
    r.session.execute.side_effect = IntegrityError("INSERT", {}, original)
    await r.worker.process(b"1-0", r.fields)
    r.worker.quarantine.assert_awaited_once_with(
        b"1-0", r.fields, "Missing URL mapping"
    )
    r.worker.acknowledge.assert_not_awaited()


async def test_ack_failure_can_be_replayed_without_increment(resources):
    r = resources
    r.worker.acknowledge.side_effect = [ConnectionError(), None]
    with pytest.raises(ConnectionError):
        await r.worker.process(b"1-0", r.fields)
    r.session.execute.return_value.scalar_one_or_none = lambda: None
    await r.worker.process(b"1-0", r.fields)
    assert r.session.execute.await_count == 3
    assert r.worker.acknowledge.await_count == 2


@pytest.mark.parametrize("recover", [False, True])
async def test_consumer_reads_new_or_recovers_abandoned_event(resources, recover):
    r = resources
    stop = asyncio.Event()
    r.client.xgroup_create = AsyncMock()
    entry = (b"1-0", r.fields)
    r.client.xautoclaim = AsyncMock(
        return_value=[b"0-0", [entry] if recover else [], []]
    )
    r.client.xreadgroup = AsyncMock(return_value=[(b"stream", [entry])])

    async def process(*args):
        stop.set()
        return "acknowledged"

    r.worker.process = AsyncMock(side_effect=process)
    await r.worker.run(stop)
    r.client.xgroup_create.assert_awaited_once_with(
        "test:visits", CONSUMER_GROUP, id="0", mkstream=True
    )
    assert r.client.xautoclaim.await_args.args[0] == "test:visits"
    r.worker.process.assert_awaited_once_with(*entry)
    assert (
        r.metrics.get_sample_value(
            "url_shortener_visit_processing_duration_seconds_count",
            {"outcome": "acknowledged"},
        )
        == 1
    )
    if recover:
        r.client.xreadgroup.assert_not_awaited()
    else:
        assert r.client.xreadgroup.await_args.args[2] == {"test:visits": ">"}


async def test_stopped_worker_does_not_consume(resources):
    stop = asyncio.Event()
    stop.set()
    await resources.worker.run(stop)
    resources.client.xreadgroup.assert_not_called()


async def test_retry_preserves_pending_event_and_backs_off(resources, monkeypatch):
    r = resources
    stop = asyncio.Event()
    delays = []

    async def wait_without_sleep(awaitable, timeout):
        awaitable.close()
        delays.append(timeout)
        raise TimeoutError

    monkeypatch.setattr(
        "url_shortener.visits.worker.asyncio.wait_for", wait_without_sleep
    )
    r.client.xgroup_create = AsyncMock()
    r.client.xautoclaim = AsyncMock(return_value=[b"0-0", [], []])
    r.client.xreadgroup = AsyncMock(return_value=[(b"stream", [(b"1-0", r.fields)])])
    attempts = 0

    async def process(*args):
        nonlocal attempts
        attempts += 1
        if attempts < 4:
            raise SQLAlchemyError("database temporarily unavailable")
        stop.set()
        return "quarantined"

    r.worker.process = AsyncMock(side_effect=process)
    await r.worker.run(stop)
    assert delays == [1, 2, 4]
    assert r.worker.process.await_count == 4
    r.client.xreadgroup.assert_awaited_once()
    count = "url_shortener_visit_processing_duration_seconds_count"
    assert r.metrics.get_sample_value(count, {"outcome": "failed"}) == 3
    assert r.metrics.get_sample_value(count, {"outcome": "quarantined"}) == 1
    assert r.metrics.get_sample_value(count, {"outcome": "acknowledged"}) == 0


async def test_shutdown_during_failed_processing_leaves_pending_event(resources):
    r = resources
    stop = asyncio.Event()
    r.client.xgroup_create = AsyncMock()
    r.client.xautoclaim = AsyncMock(return_value=[b"0-0", [(b"1-0", r.fields)], []])

    async def fail(*args):
        stop.set()
        raise SQLAlchemyError("database unavailable")

    r.worker.process = AsyncMock(side_effect=fail)
    await r.worker.run(stop)
    r.worker.acknowledge.assert_not_awaited()


async def test_ack_and_delete_share_redis_transaction(resources):
    r = resources
    pipe = MagicMock()
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=False)
    pipe.execute = AsyncMock()
    r.client.pipeline.return_value = pipe
    await VisitWorker.acknowledge(r.worker, b"1-0")
    r.client.pipeline.assert_called_once_with(transaction=True)
    pipe.xack.assert_called_once_with("test:visits", CONSUMER_GROUP, b"1-0")
    pipe.xdel.assert_called_once_with("test:visits", b"1-0")
    pipe.execute.assert_awaited_once()
