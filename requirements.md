# URL Shortener Requirements

## Scope and Technology

Implement [Task.md](Task.md) locally using Python 3.14, FastAPI, SQLModel over
async SQLAlchemy/Psycopg, PostgreSQL, Redis, and Alembic. Use uv for dependency
management. PostgreSQL is the source of truth for mappings and processed analytics.
Redis supplies mapping caching and a Stream queue. Run the API and visit worker
as separate processes; the same Docker image supports both.

See [apis.md](apis.md), [entities.md](entities.md), and [flows.md](flows.md) for
contracts, storage, and processing. Cloud deployment and Compose are outside scope.

## Functional Requirements

### FR-01: Create Independent Links

- `POST /shorten` creates a distinct code for every successful submission, even
  for the same original URL and owner. Each link has independent statistics.
- Accept absolute HTTP/HTTPS URLs with a hostname and at most 2,048 characters.
  Validate syntax without contacting the destination; preserve the submitted URL.
- Enforce uniqueness in PostgreSQL. Generate base62 codes from a shared sequence,
  skip reserved paths, and retry only code collisions, within five candidate attempts.
- Commit mappings before returning success. Never overwrite or reuse codes.

### FR-02: Ownership

- Creation and owner-only statistics require a UUID-formatted `X-User-ID` header.
  Trim surrounding whitespace; compare UUID values rather than strings.
- Assign ownership from that header; never generate a new owner for a link.
- Redirects are public. Registration, login, user existence checks, and identity
  verification remain outside scope. The trusted header permits impersonation
  and is a temporary boundary replaceable by authentication.

### FR-03: Retention

- Links do not expire and cannot be deleted through this iteration's API.
- Retain mappings, ownership, processed Visit logs, and statistics indefinitely.
- Retain failed queue entries for inspection; do not trim unprocessed events.

### FR-04: Best-Effort Redirect Analytics

- `GET /{short_code}` resolves Redis mappings first, using PostgreSQL on cache
  misses or failures. Trust valid cached mappings without a database check.
- Codes absent from both lookups return `404` without events. A stale cached
  mapping is trusted for redirecting; the worker rejects missing database mappings.
- Use a reusable decorator to publish one event per resolved redirect containing
  a UUID event ID, code, direct client IP, request UTC timestamp, and version.
- Count repeated requests from the same IP independently; count redirect operations,
  not destination-page loads or unique visitors.
- Attempt publishing before returning `302`, but redirect even if Redis publishing
  fails. Missing/unusable IP metadata skips analytics without blocking the redirect.
- Queue submission uses a single bounded attempt. A timeout may have an uncertain
  outcome. Failed publishing or Redis persistence losses can leave visits missing.
- Keep `Location` and `Cache-Control: no-store`. Creation, statistics, health,
  and unsuccessful resolution do not publish visit events.

### FR-05: Background Processing and Eventual Statistics

- Run a separate Redis Streams consumer-group worker. Consume events published
  before worker startup and recover abandoned pending deliveries.
- Insert the Visit and atomically increment its ShortLink counter in one database
  transaction. A unique event ID makes retries and duplicate deliveries no-ops.
- Preserve the producer's visit timestamp. Acknowledge/delete an event only after
  commit; database failures leave it pending for retry.
- Quarantine malformed events and references to absent mappings without modifying
  counts. Retain quarantine entries for inspection.
- `GET /stats/{short_code}` returns the owner's current committed processed count
  directly from PostgreSQL. It may lag indefinitely while workers are unavailable;
  there is no freshness SLA, and lost events may never appear.
- Counter/log equality applies to processed unique events, not every redirect.
  Queue delivery is not exactly once, and client receipt is not a database guarantee.

## Non-Functional Requirements

- Use request-scoped sessions, pooled connections, explicit transactions, database
  uniqueness/foreign keys, and atomic increments to prevent lost updates.
- Do not hold a database lookup transaction while publishing or filling the cache.
- Cache hits can redirect during PostgreSQL outages. Cache misses need PostgreSQL;
  creation/statistics still fail with `503` when PostgreSQL is unavailable.
- Redis failure does not suppress a successfully resolved redirect; it may lose
  that request's analytics. Statistics and ownership never use cached counts.
- Configure queue Redis with persistent storage, AOF (`appendfsync everysec`), and
  `noeviction`. Persistence loss is still possible; do not silently promise durability
  beyond the Redis configuration. Application code must not change server settings.
- Document redirect latency, hot-counter contention, pending-event recovery,
  deduplication, queue backlog, campaign traffic, and multi-instance trade-offs.
  No throughput benchmark or numerical latency target is required.
- Follow `AGENTS.md`: typed modular code, Ruff, mypy, and pytest unit tests using
  mocked boundaries. No coverage percentage or permanent integration suite is required.

## Deliverables and Exclusions

Deliver source, migrations, uv manifest/lockfile, exported `requirements.txt`,
Dockerfile, unit tests, API/worker startup instructions, `SCALABILITY.md`, and
supporting design and verification records.

Authentication, expiration, deletion, link editing, custom aliases, raw-log APIs,
cloud deployment, Celery/RabbitMQ, and worker batching are outside scope.
