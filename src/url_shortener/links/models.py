from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    func,
    text,
)
from sqlmodel import Field, SQLModel

SQLModel.metadata.naming_convention = {
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}


class ShortLink(SQLModel, table=True):
    __tablename__: ClassVar[str] = "short_links"
    __table_args__ = (
        CheckConstraint(
            "visit_count >= 0", name="ck_short_links_visit_count_nonnegative"
        ),
    )

    short_code: str = Field(primary_key=True)
    original_url: str = Field(max_length=2048)
    owner_id: UUID
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )
    visit_count: int = Field(
        default=0, sa_type=BigInteger, sa_column_kwargs={"server_default": text("0")}
    )
