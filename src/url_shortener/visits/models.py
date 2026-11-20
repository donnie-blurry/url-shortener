from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address
from typing import ClassVar
from uuid import UUID

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import INET
from sqlmodel import Field, SQLModel

from url_shortener.links.models import ShortLink


class Visit(SQLModel, table=True):
    __tablename__: ClassVar[str] = "visits"

    event_id: UUID = Field(primary_key=True)
    short_code: str = Field(
        foreign_key=f"{ShortLink.__tablename__}.short_code", index=True
    )
    client_ip: IPv4Address | IPv6Address = Field(sa_column=Column(INET, nullable=False))
    visited_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )
