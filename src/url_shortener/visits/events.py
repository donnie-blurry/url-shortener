from ipaddress import IPv4Address, IPv6Address
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class VisitEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    event_id: UUID
    short_code: str = Field(pattern=r"^[0-9a-zA-Z]+$", max_length=11)
    client_ip: IPv4Address | IPv6Address
    visited_at: AwareDatetime
