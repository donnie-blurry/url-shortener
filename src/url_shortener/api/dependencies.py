from collections.abc import AsyncIterator
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Header, Request
from pydantic import BeforeValidator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from url_shortener.cache import MappingCache
from url_shortener.visits.queue import VisitQueue


def strip_identity(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


OwnerId = Annotated[UUID, BeforeValidator(strip_identity)]


async def get_owner_id(
    owner_id: Annotated[
        OwnerId,
        Header(
            alias="X-User-ID",
            description=(
                "Owner UUID. Use the same value when creating a link and reading "
                "its statistics. This trusted header is not authentication."
            ),
            openapi_examples={
                "demo_owner": {
                    "summary": "Demo owner",
                    "value": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        ),
    ],
) -> UUID:
    return owner_id


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)
    async with factory() as session:
        yield session


async def get_cache(request: Request) -> MappingCache:
    return cast(MappingCache, request.app.state.mapping_cache)


async def get_queue(request: Request) -> VisitQueue:
    return cast(VisitQueue, request.app.state.visit_queue)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
OwnerDep = Annotated[UUID, Depends(get_owner_id)]
CacheDep = Annotated[MappingCache, Depends(get_cache)]
QueueDep = Annotated[VisitQueue, Depends(get_queue)]
