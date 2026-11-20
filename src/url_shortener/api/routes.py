from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text
from sqlmodel import col

from url_shortener.api.dependencies import (
    CacheDep,
    OwnerDep,
    QueueDep,
    SessionDep,
    SettingsDep,
)
from url_shortener.links.models import ShortLink
from url_shortener.links.schemas import CreateLink, LinkResponse, StatsResponse
from url_shortener.links.services import create_link, find_link
from url_shortener.visits.decorator import record_visit

router = APIRouter()


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    await session.scalar(text("SELECT 1"))
    return {"status": "OK"}


@router.post("/shorten", response_model=LinkResponse, status_code=201)
async def shorten(
    body: CreateLink, session: SessionDep, owner_id: OwnerDep, settings: SettingsDep
) -> LinkResponse:
    link = await create_link(
        session,
        body.original_url,
        owner_id,
        max_code_attempts=settings.max_code_attempts,
    )
    return LinkResponse.model_validate(link)


@router.get("/stats/{short_code}", response_model=StatsResponse)
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


@router.get("/{short_code}", response_class=RedirectResponse, status_code=302)
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
