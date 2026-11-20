# Entity Model

SQLModel tables and Alembic migrations implement [requirements.md](requirements.md).
PostgreSQL stores mappings and processed analytics. Redis stores cached mappings,
queued events, and failed events; it is not the statistics source of truth.

## ShortLink

| Field | Storage | Rules |
| --- | --- | --- |
| `short_code` | String primary key | Immutable, unique, permanently reserved |
| `original_url` | VARCHAR(2048) | Validated absolute HTTP/HTTPS URL; deliberately not unique |
| `owner_id` | PostgreSQL UUID | Required; supplied identity, never generated per link |
| `created_at` | Timezone-aware timestamp | UTC application default and database default |
| `visit_count` | BIGINT | Nonnegative, starts at zero; counts processed events |

Each submission creates a new mapping even for an existing URL. No User table,
expiration field, or deletion state exists. Future verified provider identities
should map to internal user UUIDs rather than become link owners directly.

## Visit

| Field | Storage | Rules |
| --- | --- | --- |
| `id` | BIGINT identity primary key | Generated for the persisted row |
| `event_id` | Unique non-null UUID | Stable producer event identity; deduplicates replay |
| `short_code` | Indexed foreign key | References an existing ShortLink |
| `client_ip` | INET | IPv4/IPv6 direct-peer address captured by the API |
| `visited_at` | Timezone-aware timestamp | Producer's request time, not worker processing time |

All persisted fields are non-null. Multiple events may share a code, IP, and
similar timestamps. Retain processed visits indefinitely. Migration `0002` assigns
UUIDs to pre-existing visits before enforcing uniqueness; their counters and other
fields remain unchanged.

## Queue Event

The Redis Stream stores a JSON `payload` with these fields:

| Field | Wire type | Rules |
| --- | --- | --- |
| `version` | Integer | Version 1 |
| `event_id` | UUID string | New per redirect; unchanged across delivery retries |
| `short_code` | String | Base62, maximum 11 characters |
| `client_ip` | IP string | Direct client address |
| `visited_at` | Timezone-aware ISO timestamp | Request time |

Producer metadata is validated before enqueueing. Workers validate the untrusted
payload at their boundary, including required event identity and timestamp.
Malformed payloads do not receive newly generated identities on replay.

## Consistency and Relationships

One ShortLink has zero or more Visits; each Visit belongs to exactly one mapping.
For each link, `visit_count` equals its committed Visit-row count. This invariant
covers processed unique events, not all redirects or pending messages.

The worker inserts with `ON CONFLICT (event_id) DO NOTHING RETURNING id` and
increments the counter only for a new insertion, within one READ COMMITTED
transaction. The foreign key prevents orphan rows. A duplicate event causes no
counter change. Redis acknowledgement happens only after commit, so replay after
a worker crash or lost acknowledgement is safe for database effects.

Unprocessed events live in `url-shortener:visits`. Invalid or missing-mapping events
move to `url-shortener:visits:failed` for inspection without creating Visit rows.
Redis persistence or failed publishing can lose events; no exactly-once queue
delivery or lossless relationship between redirects and counts is claimed.

## Mapping Storage

A separate non-cycling PostgreSQL sequence starting at 1 supplies numbers encoded
with `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`. Reserved
route names are skipped. Sequence gaps and predictable codes are accepted.

Redis caches immutable code-to-destination mappings for one hour. Cached mappings
are trusted without a PostgreSQL existence check; the worker validates references
when persisting events. Statistics and ownership always read PostgreSQL.
