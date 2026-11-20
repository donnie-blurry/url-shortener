from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Sequence, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from url_shortener.links.codes import MAX_CODE_ATTEMPTS, RESERVED_CODES, encode_code
from url_shortener.links.models import ShortLink

SHORT_CODE_SEQUENCE = Sequence("short_code_sequence", start=1)


async def create_link(
    session: AsyncSession, original_url: str, owner_id: UUID
) -> ShortLink:
    for _ in range(MAX_CODE_ATTEMPTS):
        try:
            async with session.begin():
                number = await session.scalar(SHORT_CODE_SEQUENCE.next_value())
                if number is None:
                    raise HTTPException(503, "Code allocation unavailable")
                code = encode_code(number)
                if code in RESERVED_CODES:
                    continue
                link = ShortLink(
                    short_code=code, original_url=original_url, owner_id=owner_id
                )
                session.add(link)
                await session.flush()
            return link
        except IntegrityError as exc:
            original = exc.orig
            diagnostic = getattr(original, "diag", None)
            if not (
                getattr(original, "sqlstate", None) == "23505"
                and getattr(diagnostic, "constraint_name", None) == "pk_short_links"
            ):
                raise
    raise HTTPException(503, "Code allocation unavailable")


async def find_link(session: AsyncSession, short_code: str) -> ShortLink:
    link = (
        await session.execute(
            select(ShortLink).where(col(ShortLink.short_code) == short_code)
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(404, "Short code not found")
    return link
