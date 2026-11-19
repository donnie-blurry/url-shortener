# API Contracts

This document specifies the intended API for [requirements.md](requirements.md).
It describes the implemented endpoints.
Expiration and deletion are outside scope: there is no DELETE endpoint,
expiration input, or lifecycle-state field.

## Shared Conventions

- Requests and response bodies use JSON unless stated otherwise.
- Timestamps use timezone-aware ISO 8601 values in UTC, such as
  `2026-11-19T12:00:00Z`.
- Creation and statistics require `X-User-ID`, a UUID identifying the owner.
  Missing, blank, or malformed UUID values return `422`. Surrounding whitespace
  is stripped; equivalent UUID representations identify the same owner.
- The header is trusted without authentication for this iteration. Ownership
  checks compare UUID values, not their string representations.
  Identity extraction must be replaceable by future authentication.
- Redirects and health checks are public.
- Validation errors return `422` using FastAPI's standard validation-error
  response. Other documented errors use a JSON `detail` string.
- Unavailable PostgreSQL or a failed visit-recording operation returns `503`.
  Redis unavailability alone does not cause a request to fail: use PostgreSQL.
- Only successful redirect operations record visits; creation, statistics,
  health checks, and error responses do not.

## Create a Link

**`POST /shorten`**

Required header:

```http
X-User-ID: 550e8400-e29b-41d4-a716-446655440000
```

Request:

```json
{
  "original_url": "https://example.com/article"
}
```

`original_url` is required, must be an absolute HTTP/HTTPS URL with a hostname,
and must contain no more than 2,048 characters. Validate syntax without
contacting the destination. There is no `expires_at` request field.

Response: **`201 Created`**

```json
{
  "short_code": "aB3xY7",
  "original_url": "https://example.com/article",
  "created_at": "2026-11-19T12:00:00Z"
}
```

Every successful request creates a distinct code, including repeated or
concurrent submissions of the same original URL. Codes are variable-length
base62 encodings of PostgreSQL sequence values; the example is illustrative.

| Condition | Status |
| --- | --- |
| Mapping committed successfully | `201 Created` |
| Invalid body, URL, or user-ID header | `422 Unprocessable Content` |
| Database unavailable or code-generation retries exhausted | `503 Service Unavailable` |

## Follow a Link

**`GET /{short_code}`**

No user-ID header or request body is required.

Response: **`302 Found`**, with no required response-body schema:

```http
Location: https://example.com/article
Cache-Control: no-store
```

Before returning the redirect, commit the visit log and counter increment
together. If recording fails, roll back and return an error without redirecting.
Repeated visits from the same IP count separately. A cache hit does not bypass
durable visit recording.

| Condition | Status |
| --- | --- |
| Known code and visit committed | `302 Found` |
| Unknown code | `404 Not Found` |
| Database unavailable or visit recording fails | `503 Service Unavailable` |

Unknown codes create neither visit logs nor counter increments. There is no
`410 Gone` response because expiration and deletion are outside scope.

## Retrieve Statistics

**`GET /stats/{short_code}`**

Requires `X-User-ID`. No request body.

Response: **`200 OK`**, with `Cache-Control: no-store`:

```json
{
  "short_code": "aB3xY7",
  "original_url": "https://example.com/article",
  "visit_count": 42,
  "created_at": "2026-11-19T12:00:00Z"
}
```

Return only to the owner. Read the current committed count from PostgreSQL;
do not serve stale cached statistics. New links return `visit_count: 0`.
Individual visit logs and IP addresses are not exposed by this API.

| Condition | Status |
| --- | --- |
| Existing link owned by the requester | `200 OK` |
| Unknown code | `404 Not Found` |
| Requester is not the owner | `403 Forbidden` |
| Missing or invalid user-ID header | `422 Unprocessable Content` |
| Database unavailable | `503 Service Unavailable` |

## Health Check

**`GET /health`** returns **`200 OK`** with:

```json
{"status": "OK"}
```

This executes `SELECT 1` through a request-scoped session. Database failures
return `503`; Redis is not checked. It is a PostgreSQL readiness check.
Static API routes must take precedence over the short-code route; generated
codes must not conflict with reserved API paths.
