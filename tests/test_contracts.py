from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI
from pydantic import ValidationError

from url_shortener.identity import get_owner_id
from url_shortener.schemas import CreateLink, LinkResponse


@pytest.mark.parametrize(
    "url",
    [
        "/relative",
        "example.com",
        "ftp://example.com",
        "javascript:alert(1)",
        "https:///path",
        "http:example.com",
        "https://example.com/a b",
        "",
        "https://",
        "https://example.com/" + "x" * 2048,
    ],
)
def test_reject_invalid_urls(url):
    with pytest.raises(ValidationError):
        CreateLink(original_url=url)


def test_preserve_valid_url_and_reject_extra_fields():
    url = "https://example.com/?x=a%2Fb#section"
    assert CreateLink(original_url=url).original_url == url
    assert CreateLink(original_url="https://example.com/" + "x" * 2028)
    with pytest.raises(ValidationError):
        CreateLink.model_validate({"original_url": url, "owner_id": str(uuid4())})


def test_serialize_timestamps_in_utc():
    response = LinkResponse(
        short_code="1",
        original_url="https://example.com",
        created_at=datetime(
            2026,
            1,
            1,
            12,
            tzinfo=timezone(timedelta(hours=3)),
        ),
    )
    assert response.model_dump(mode="json")["created_at"] == "2026-01-01T09:00:00Z"


@pytest.fixture
def identity_app():
    app = FastAPI()

    @app.get("/")
    async def identity(owner: Annotated[UUID, Depends(get_owner_id)]):
        return {"owner": str(owner)}

    return app


@pytest.mark.parametrize("value", [None, "", "  ", "user-123", "not-a-uuid"])
async def test_invalid_identity_is_422(identity_app, value):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=identity_app), base_url="http://test"
    ) as client:
        headers = {} if value is None else {"X-User-ID": value}
        response = await client.get("/", headers=headers)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


async def test_equivalent_uuid_headers_resolve_to_same_owner(identity_app):
    owner = uuid4()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=identity_app), base_url="http://test"
    ) as client:
        for value in [str(owner), owner.hex.upper(), "  " + str(owner) + "  "]:
            response = await client.get("/", headers={"X-User-ID": value})
            assert response.status_code == 200
            assert response.json() == {"owner": str(owner)}
