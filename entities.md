# Entity Model

This is the implemented model for [requirements.md](requirements.md) and
[apis.md](apis.md). SQLModel tables and Alembic migrations implement it. PostgreSQL
stores both entities durably; Redis stores disposable cached mapping data.

## ShortLink

Represents one independently tracked shortened URL.

| Field | Logical type | Rules |
| --- | --- | --- |
| `short_code` | String | Unique, immutable identifier; permanently reserved |
| `original_url` | String | Absolute HTTP/HTTPS URL with a hostname; maximum 2,048 characters |
| `owner_id` | UUID | Required PostgreSQL UUID obtained from the validated trusted header; no generated default |
| `created_at` | Timezone-aware timestamp | Creation time, represented in UTC |
| `visit_count` | Integer | Starts at zero; never negative; incremented atomically |

All fields are required. `original_url` is not unique: even the same owner
submitting the same URL receives a separate ShortLink with its own statistics.
`owner_id` does not reference a User entity because accounts are outside scope.

There are no `expires_at`, `is_expired`, `is_deleted`, or `deleted_at` fields.
Links have no expiration or deletion lifecycle in this iteration.

## Visit

Represents one recorded redirect, not a unique visitor or a destination-page load.

| Field | Logical type | Rules |
| --- | --- | --- |
| `id` | Generated identifier | Uniquely identifies the individual visit |
| `short_code` | String reference | References an existing ShortLink |
| `client_ip` | IP address | Direct client address; supports IPv4 and IPv6 |
| `visited_at` | Timezone-aware timestamp | Time the visit was recorded, represented in UTC |

All fields are required. Multiple Visit records may have the same client IP
and short code. Retain all visit records indefinitely. Proxy-aware IP extraction
is deferred; do not trust arbitrary forwarded headers.

## Relationship and Integrity

One ShortLink has zero or more Visits; each Visit belongs to exactly one ShortLink.
Enforce code uniqueness and the Visit-to-ShortLink reference in PostgreSQL.
Unknown codes must not produce Visit records.

For every ShortLink, `visit_count` equals the number of committed Visit records
associated with that code. Insert the Visit and increment the counter within
the same transaction. Use an atomic database increment rather than reading a
counter into application memory and writing back an incremented value.

Commit before returning a redirect. On transaction failure, neither change
persists and the request must not redirect. This provides immediate statistics
without making response delivery to the browser part of the database transaction.

## Access and Storage Responsibilities

- Creation assigns ownership from `X-User-ID`; clients do not supply `owner_id`
  in the request body.
- Redirects are public. Statistics require the stored owner ID to match the
  requester ID.
- Persist IP/timestamp logs through reusable decorator or middleware infrastructure.
- Read statistics from the durable aggregate counter; do not count the entire
  visit log for each statistics request.
- Redis is optional for correctness. Cache failures fall back to PostgreSQL;
  cached mapping reads never replace PostgreSQL analytics writes.

## Physical Design

ShortLink uses a string short-code primary key, VARCHAR(2048) original URL,
native UUID owner, timezone-aware timestamps, and a nonnegative BIGINT counter.
Visit uses a BIGINT identity primary key, indexed short-code foreign key,
INET client address, and timezone-aware timestamp. Application timestamp defaults
use UTC; database defaults also support inserts outside the ORM.

A separate non-cycling PostgreSQL sequence starting at 1 supplies code numbers,
encoded with `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`.
Codes are variable-length, predictable, and may have gaps. No User table is
needed until authentication is introduced; external provider subjects should
then map to application user UUIDs rather than become link owners directly.
