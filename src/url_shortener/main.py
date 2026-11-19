from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.database import engine, get_session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(
        session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, str]:
    try:
        await session.scalar(text("SELECT 1"))
    except SQLAlchemyError as exception:
        raise HTTPException(
            status_code=503,
            detail="Database error"
        ) from exception

    return {"status": "OK"}
