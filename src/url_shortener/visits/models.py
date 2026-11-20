from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Column, DateTime, Identity, func
from sqlalchemy.dialects.postgresql import INET
from sqlmodel import Field, SQLModel

from url_shortener.links.models import ShortLink


class Visit(SQLModel, table=True):
    __tablename__: ClassVar[str] = "visits"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, Identity(), primary_key=True)
    )
    event_id: UUID = Field(default_factory=uuid4, unique=True)
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
