import asyncio
import logging
import time
from typing import cast
from uuid import uuid4

from pydantic import ValidationError
from redis.exceptions import RedisError, ResponseError
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col

from url_shortener.links.models import ShortLink
from url_shortener.visits.events import VisitEvent
from url_shortener.visits.models import Visit
from url_shortener.visits.queue import CONSUMER_GROUP, VisitQueue

logger = logging.getLogger(__name__)
StreamEntry = tuple[bytes, dict[bytes, bytes]]


class VisitWorker:
    def __init__(
        self, queue: VisitQueue, sessions: async_sessionmaker[AsyncSession]
    ) -> None:
        self.queue = queue
        self.sessions = sessions
        self.consumer = f"worker-{uuid4()}"

    async def acknowledge(self, message_id: bytes) -> None:
        async with self.queue.client.pipeline(transaction=True) as pipe:
            pipe.xack(self.queue.stream, CONSUMER_GROUP, message_id)
            pipe.xdel(self.queue.stream, message_id)
            await pipe.execute()

    async def quarantine(
        self, message_id: bytes, fields: dict[bytes, bytes], reason: str
    ) -> None:
        async with self.queue.client.pipeline(transaction=True) as pipe:
            pipe.xadd(
                self.queue.failed_stream,
                {
                    "source_id": message_id,
                    "reason": reason,
                    "payload": fields.get(b"payload", b""),
                },
            )
            pipe.xack(self.queue.stream, CONSUMER_GROUP, message_id)
            pipe.xdel(self.queue.stream, message_id)
            await pipe.execute()
        logger.warning("Quarantined visit event: %s", reason)

    async def process(self, message_id: bytes, fields: dict[bytes, bytes]) -> None:
        try:
            event = VisitEvent.model_validate_json(fields.get(b"payload", b""))
        except ValidationError:
            await self.quarantine(message_id, fields, "Invalid visit event")
            return

        try:
            await self._persist_visit(event)
        except IntegrityError as exc:
            if (
                getattr(exc.orig, "sqlstate", None) == "23503"
                and getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                == "fk_visits_short_code_short_links"
            ):
                await self.quarantine(message_id, fields, "Missing URL mapping")
                return
            raise
        await self.acknowledge(message_id)

    async def run(self, stop: asyncio.Event) -> None:
        initialized = False
        current: StreamEntry | None = None
        claim_cursor = b"0-0"
        next_claim = 0.0
        delay = 1.0
        while not stop.is_set():
            try:
                if not initialized:
                    await self._ensure_consumer_group()
                    initialized = True
                if current is None and time.monotonic() >= next_claim:
                    claim_cursor, current = await self._claim_pending(claim_cursor)
                    next_claim = time.monotonic() + 5
                if current is None:
                    current = await self._read_new_message()
                if current is None:
                    continue
                await self.process(*current)
                current = None
                delay = 1.0
            except RedisError, SQLAlchemyError:
                logger.warning(
                    "Visit worker failed; event remains pending for retry",
                    exc_info=True,
                )
                initialized = False
                try:
                    await asyncio.wait_for(stop.wait(), timeout=delay)
                except TimeoutError:
                    pass
                delay = min(delay * 2, 30)

    async def _ensure_consumer_group(self) -> None:
        try:
            await self.queue.client.xgroup_create(
                self.queue.stream, CONSUMER_GROUP, id="0", mkstream=True
            )
        except ResponseError as exc:
            if not str(exc).startswith("BUSYGROUP"):
                raise

    async def _claim_pending(self, cursor: bytes) -> tuple[bytes, StreamEntry | None]:
        claimed = await self.queue.client.xautoclaim(
            self.queue.stream,
            CONSUMER_GROUP,
            self.consumer,
            min_idle_time=60_000,
            start_id=cursor,
            count=1,
        )
        next_cursor, entries = claimed[0], claimed[1]
        return next_cursor, entries[0] if entries else None

    async def _read_new_message(self) -> StreamEntry | None:
        messages = cast(
            list[tuple[bytes, list[StreamEntry]]],
            await self.queue.client.xreadgroup(
                CONSUMER_GROUP,
                self.consumer,
                {self.queue.stream: ">"},
                count=1,
                block=1000,
            ),
        )
        return messages[0][1][0] if messages else None

    async def _persist_visit(self, event: VisitEvent) -> None:
        async with self.sessions() as session, session.begin():
            result = await session.execute(
                insert(Visit)
                .values(
                    event_id=event.event_id,
                    short_code=event.short_code,
                    client_ip=event.client_ip,
                    visited_at=event.visited_at,
                )
                .on_conflict_do_nothing(index_elements=[col(Visit.event_id)])
                .returning(col(Visit.event_id))
            )
            if result.scalar_one_or_none() is not None:
                await session.execute(
                    update(ShortLink)
                    .where(col(ShortLink.short_code) == event.short_code)
                    .values(visit_count=col(ShortLink.visit_count) + 1)
                )
