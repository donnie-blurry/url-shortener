from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from url_shortener.analytics import record_visit
from url_shortener.cache import MappingCache, create_cache, get_cache
from url_shortener.config import Settings
from url_shortener.database import create_database, get_session
from url_shortener.identity import get_owner_id
from url_shortener.models import ShortLink
from url_shortener.queue import VisitQueue, create_queue, get_queue
from url_shortener.schemas import CreateLink, LinkResponse, StatsResponse
from url_shortener.services import create_link, find_link

SessionDep = Annotated[AsyncSession, Depends(get_session)]
OwnerDep = Annotated[UUID, Depends(get_owner_id)]
CacheDep = Annotated[MappingCache, Depends(get_cache)]
QueueDep = Annotated[VisitQueue, Depends(get_queue)]


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configuration = settings if settings is not None else Settings()
        engine, factory = create_database(configuration)
        cache = create_cache(str(configuration.redis_url))
        queue = create_queue(str(configuration.redis_url))
        application.state.session_factory = factory
        application.state.mapping_cache = cache
        application.state.visit_queue = queue
        try:
            yield
        finally:
            try:
                try:
                    await cache.client.aclose()
                finally:
                    await queue.client.aclose()
            finally:
                await engine.dispose()

    application = FastAPI(title="URL Shortener", lifespan=lifespan)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @application.get("/health")
    async def health(session: SessionDep) -> dict[str, str]:
        await session.scalar(text("SELECT 1"))
        return {"status": "OK"}

    @application.post("/shorten", response_model=LinkResponse, status_code=201)
    async def shorten(
        body: CreateLink, session: SessionDep, owner_id: OwnerDep
    ) -> LinkResponse:
        link = await create_link(session, body.original_url, owner_id)
        return LinkResponse.model_validate(link)

    @application.get("/stats/{short_code}", response_model=StatsResponse)
    async def statistics(
        short_code: str,
        response: Response,
        session: SessionDep,
        owner_id: OwnerDep,
    ) -> StatsResponse:
        link = await find_link(session, short_code)
        if link.owner_id != owner_id:
            raise HTTPException(403, "Forbidden")
        response.headers["Cache-Control"] = "no-store"
        return StatsResponse.model_validate(link)

    @application.get("/{short_code}", response_class=RedirectResponse, status_code=302)
    @record_visit
    async def redirect(
        short_code: str,
        request: Request,
        session: SessionDep,
        cache: CacheDep,
        queue: QueueDep,
    ) -> RedirectResponse:
        destination = await cache.get(short_code)
        if destination is None:
            async with session.begin():
                destination = (
                    await session.execute(
                        select(col(ShortLink.original_url)).where(
                            col(ShortLink.short_code) == short_code
                        )
                    )
                ).scalar_one_or_none()
            if destination is None:
                raise HTTPException(404, "Short code not found")
            await cache.set(short_code, destination)
        return RedirectResponse(
            destination, status_code=302, headers={"Cache-Control": "no-store"}
        )

    return application


app = create_app()
