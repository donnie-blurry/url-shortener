from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from url_shortener.api.routes import router
from url_shortener.cache import create_cache
from url_shortener.config import Settings
from url_shortener.database import create_database
from url_shortener.visits.queue import create_queue


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configuration = settings if settings is not None else Settings()
        async with AsyncExitStack() as stack:
            engine, factory = create_database(configuration)
            stack.push_async_callback(engine.dispose)

            cache = create_cache(str(configuration.redis_url))
            stack.push_async_callback(cache.client.aclose)

            queue = create_queue(str(configuration.redis_url))
            stack.push_async_callback(queue.client.aclose)

            application.state.session_factory = factory
            application.state.mapping_cache = cache
            application.state.visit_queue = queue
            yield

    application = FastAPI(title="URL Shortener", lifespan=lifespan)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    application.include_router(router)
    return application


app = create_app()
