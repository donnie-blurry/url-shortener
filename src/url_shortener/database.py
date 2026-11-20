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
        connect_args={"connect_timeout": 5},
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)
