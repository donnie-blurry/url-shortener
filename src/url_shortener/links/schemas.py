from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    field_serializer,
    field_validator,
)

HTTP_URL = TypeAdapter(HttpUrl)


class CreateLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_url: Annotated[str, Field(min_length=1, max_length=2048)]

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        HTTP_URL.validate_python(value)
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not parsed.hostname
        ):
            raise ValueError("An absolute HTTP/HTTPS URL with a hostname is required")
        if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("URL must not contain whitespace or control characters")
        return value


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    short_code: str
    original_url: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class StatsResponse(LinkResponse):
    visit_count: int
