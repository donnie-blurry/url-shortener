import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import wraps
from uuid import uuid4

from fastapi import Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.cache import MappingCache
from url_shortener.queue import VisitEvent, VisitQueue

logger = logging.getLogger(__name__)
RedirectHandler = Callable[
    [str, Request, AsyncSession, MappingCache, VisitQueue], Awaitable[RedirectResponse]
]


def record_visit(handler: RedirectHandler) -> RedirectHandler:
    @wraps(handler)
    async def wrapped(
        short_code: str,
        request: Request,
        session: AsyncSession,
        cache: MappingCache,
        queue: VisitQueue,
    ) -> RedirectResponse:
        visited_at = datetime.now(UTC)
        response = await handler(short_code, request, session, cache, queue)
        if request.client is None:
            logger.warning("Visit skipped because client IP is unavailable")
            return response
        try:
            event = VisitEvent(
                event_id=uuid4(),
                short_code=short_code,
                client_ip=request.client.host,
                visited_at=visited_at,
            )
        except ValidationError:
            logger.warning("Visit skipped because request metadata is invalid")
            return response
        await queue.publish(event)
        return response

    return wrapped
