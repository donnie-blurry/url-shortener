from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from url_shortener.config import Settings


def create_database(
    settings: Settings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)
