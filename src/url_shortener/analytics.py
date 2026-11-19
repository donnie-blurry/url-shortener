from collections.abc import Awaitable, Callable
from functools import wraps
from ipaddress import ip_address

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from url_shortener.cache import MappingCache
from url_shortener.models import ShortLink, Visit

RedirectHandler = Callable[
    [str, Request, AsyncSession, MappingCache], Awaitable[RedirectResponse]
]


def record_visit(handler: RedirectHandler) -> RedirectHandler:
    @wraps(handler)
    async def wrapped(
        short_code: str,
        request: Request,
        session: AsyncSession,
        cache: MappingCache,
    ) -> RedirectResponse:
        try:
            address = ip_address(request.client.host) if request.client else None
        except ValueError:
            address = None
        if address is None:
            raise HTTPException(503, "Client address unavailable")

        try:
            async with session.begin():
                response = await handler(short_code, request, session, cache)
                result = await session.execute(
                    update(ShortLink)
                    .where(col(ShortLink.short_code) == short_code)
                    .values(visit_count=col(ShortLink.visit_count) + 1)
                    .returning(col(ShortLink.short_code))
                )
                if result.scalar_one_or_none() is None:
                    raise HTTPException(404, "Short code not found")
                session.add(Visit(short_code=short_code, client_ip=address))
                await session.flush()
        except HTTPException as exc:
            if exc.status_code == 404:
                await cache.delete(short_code)
            raise

        if getattr(request.state, "mapping_cache_missed", False):
            await cache.set(short_code, request.state.original_destination)
        return response

    return wrapped
