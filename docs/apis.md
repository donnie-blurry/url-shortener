# API Contracts

These endpoints implement [requirements.md](requirements.md). Deletion and
expiration are outside scope. Analytics is best effort and processed by a worker.

## Conventions

- JSON request/response bodies; UTC ISO 8601 timestamps.
- Creation and statistics require `X-User-ID`, parsed as UUID after trimming
  whitespace. Missing/blank/malformed values return FastAPI-style `422` errors.
  Equivalent UUID representations identify the same owner.
- The header is trusted, not authenticated. Identity verification is deferred.
- Other errors use a JSON `detail` string. PostgreSQL failures return `503` on
  operations that require it. Publishing failure alone never fails a redirect.
- Only resolved redirects publish analytics. Counts represent unique processed
  events and may lag or permanently omit lost events. No freshness SLA is promised.

## POST /shorten

Required header: `X-User-ID: 550e8400-e29b-41d4-a716-446655440000`.

Request:

```json
{"original_url": "https://example.com/article"}
```

Require an absolute HTTP/HTTPS URL with a hostname, maximum 2,048 characters,
without whitespace/control characters. Reject extra fields. Do not fetch URLs.

Response: **201 Created**

```json
{
  "short_code": "1",
  "original_url": "https://example.com/article",
  "created_at": "2026-11-20T12:00:00Z"
}
```

Every successful submission creates an independent mapping. Codes are predictable,
variable-length base62 sequence values, not secrets. Return `422` for invalid
input and `503` for database failures or code-allocation exhaustion.

## GET /{short_code}

Public; no user header or body required. Resolve a trusted cached mapping or fall
back to PostgreSQL. Cache hits do not access PostgreSQL, including during outages.

Response: **302 Found**

```http
Location: https://example.com/article
Cache-Control: no-store
```

The decorator attempts one event publish before returning. Redis publishing errors,
missing IP metadata, and a stopped worker do not prevent this response. A timeout
can mean the event was accepted without its acknowledgement reaching the API.

Return `404` if neither cache nor database resolves the code. Return `503` when
PostgreSQL is required for a cache miss but unavailable. A syntactically valid
cached mapping is trusted even if its database row is absent; such an event will
be quarantined by the worker. There are no expiration/deletion checks or `410`.

## GET /stats/{short_code}

Requires owner UUID header. No body. Response: **200 OK**, `Cache-Control: no-store`.

```json
{
  "short_code": "1",
  "original_url": "https://example.com/article",
  "visit_count": 42,
  "created_at": "2026-11-20T12:00:00Z"
}
```

Read the committed aggregate directly from PostgreSQL, not Redis or a scan of
Visit rows. New links report zero. Redirects do not immediately change this value;
workers update it asynchronously. Worker downtime causes lag, and lost events can
leave permanent undercounts. Do not expose IPs, individual logs, or queue contents.

| Condition | Status |
| --- | --- |
| Known link owned by requester | `200` |
| Unknown link | `404` |
| Another owner | `403` |
| Missing/invalid UUID header | `422` |
| PostgreSQL unavailable | `503` |

## GET /health

Public PostgreSQL readiness check using `SELECT 1`. Return `200 {"status":"OK"}`
or `503` on database failure. It checks neither Redis nor the worker and emits no
visit event. Cached redirects may still work while this check returns `503`.

## Worker Interface

Run separately with `uv run python -m url_shortener.worker`, or override the Docker
image command with `python -m url_shortener.worker`. There is no worker HTTP API.
See [flows.md](flows.md) for Stream names, event schema, acknowledgement, and retries.
