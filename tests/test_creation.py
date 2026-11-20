from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.links.codes import ALPHABET, encode_code
from url_shortener.links.services import create_link


@pytest.fixture
def session():
    session = MagicMock(spec=AsyncSession)
    session.begin.return_value = MagicMock(
        __aenter__=AsyncMock(), __aexit__=AsyncMock(return_value=False)
    )
    session.scalar = AsyncMock(side_effect=range(1, 20))
    session.flush = AsyncMock()
    session.add.side_effect = lambda link: setattr(
        link, "created_at", datetime.now(UTC)
    )
    return session


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (1, "1"),
        (9, "9"),
        (10, "a"),
        (35, "z"),
        (36, "A"),
        (61, "Z"),
        (62, "10"),
        (3844, "100"),
    ],
)
def test_base62_boundaries(number, expected):
    assert encode_code(number) == expected


@pytest.mark.parametrize("number", [0, -1])
def test_sequence_values_must_be_positive(number):
    with pytest.raises(ValueError):
        encode_code(number)


async def test_each_submission_allocates_independent_link(session):
    owner = uuid4()
    first = await create_link(session, "https://example.com", owner)
    second = await create_link(session, "https://example.com", owner)
    assert first.short_code != second.short_code
    assert first.owner_id == second.owner_id == owner
    assert first.visit_count == second.visit_count == 0
    assert session.begin.return_value.__aexit__.await_count == 2


async def test_skip_reserved_code(session):
    number = sum(
        ALPHABET.index(char) * 62**index for index, char in enumerate(reversed("docs"))
    )
    session.scalar.side_effect = [number, number + 1]
    link = await create_link(session, "https://example.com", uuid4())
    assert link.short_code != "docs"
    assert session.add.call_count == 1


def integrity_error(name="pk_short_links", sqlstate="23505"):
    original = Exception("database constraint")
    original.sqlstate = sqlstate
    original.diag = SimpleNamespace(constraint_name=name)
    return IntegrityError("INSERT", {}, original)


async def test_retry_only_short_code_collision_after_transaction_exit(session):
    session.flush.side_effect = [integrity_error(), None]
    link = await create_link(session, "https://example.com", uuid4())
    assert link.short_code == "2"
    assert session.begin.call_count == 2
    first_exit = session.begin.return_value.__aexit__.await_args_list[0]
    assert first_exit.args[0] is IntegrityError


async def test_collision_exhaustion_is_503(session):
    session.flush.side_effect = integrity_error()
    with pytest.raises(HTTPException) as error:
        await create_link(session, "https://example.com", uuid4())
    assert error.value.status_code == 503
    assert session.scalar.await_count == 5


async def test_unrelated_integrity_failure_is_not_retried(session):
    session.flush.side_effect = integrity_error(name="unrelated_constraint")
    with pytest.raises(IntegrityError):
        await create_link(session, "https://example.com", uuid4())
    assert session.scalar.await_count == 1


async def test_code_allocation_failure_is_503(session):
    session.scalar.side_effect = None
    session.scalar.return_value = None
    with pytest.raises(HTTPException) as error:
        await create_link(session, "https://example.com", uuid4())
    assert error.value.status_code == 503
