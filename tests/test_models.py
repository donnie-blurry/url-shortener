from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint
from sqlalchemy.dialects.postgresql import INET
from sqlmodel import SQLModel

from url_shortener.models import ShortLink, Visit


def test_schema_preserves_uuid_ownership_and_independent_urls():
    table = SQLModel.metadata.tables["short_links"]
    assert table.primary_key.name == "pk_short_links"
    assert list(table.primary_key.columns.keys()) == ["short_code"]
    assert table.c.original_url.type.length == 2048
    assert not table.c.original_url.unique
    assert table.c.owner_id.type.as_uuid
    assert not table.c.owner_id.nullable
    assert isinstance(table.c.visit_count.type, BigInteger)
    assert any(isinstance(c, CheckConstraint) for c in table.constraints)
    assert not {"expires_at", "is_deleted"}.intersection(table.c.keys())
    owner = uuid4()
    assert (
        ShortLink(
            short_code="1", original_url="https://example.com", owner_id=owner
        ).owner_id
        == owner
    )


def test_visits_reference_existing_links_and_support_ip_addresses():
    table = SQLModel.metadata.tables["visits"]
    assert isinstance(table.c.client_ip.type, INET)
    assert table.c.short_code.index
    assert (
        next(iter(table.c.short_code.foreign_keys)).target_fullname
        == "short_links.short_code"
    )
    assert table.c.id.identity is not None
    assert Visit.__tablename__ == "visits"
