from typing import Annotated
from uuid import UUID

from fastapi import Header
from pydantic import BeforeValidator


def strip_identity(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


OwnerId = Annotated[UUID, BeforeValidator(strip_identity)]


async def get_owner_id(owner_id: Annotated[OwnerId, Header(alias="X-User-ID")]) -> UUID:
    return owner_id
