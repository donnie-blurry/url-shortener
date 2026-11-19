# URL Shortener Requirements

## Scope and Technology

Deliver a locally runnable URL shortener for the assignment described in
[Task.md](Task.md). Use Python 3.14, FastAPI, SQLModel with async SQLAlchemy, PostgreSQL, Redis,
and Alembic. PostgreSQL is the durable source of truth; Redis is a cache.
Use uv for dependency management and provide an application Dockerfile.
Cloud deployment and Docker Compose are not required for this iteration.

This document records implemented behavior and its acceptance requirements.
API contracts are documented in [apis.md](apis.md), and the entity model is
documented in [entities.md](entities.md). Implementation details remain separate.

## Functional Requirements

### FR-01: Create Independently Tracked Links

- Provide `POST /shorten`.
- Every successful submission creates a new, unique short code, even when
  another submission has the same original URL or owner.
- Each link has independent visit statistics and logs.
- Accept only absolute HTTP/HTTPS URLs with a hostname. Validate syntax without
  contacting the destination; destination availability is not checked.
- Limit original URLs to 2,048 characters. No additional destination filtering
  is required in this iteration.
- Handle code collisions, including concurrent creation, without overwriting
  an existing mapping. Permanently reserve codes; never reuse them.

### FR-02: Identify Owners

- Require a trusted, UUID-formatted `X-User-ID` header for creation and statistics.
- Associate each new link with the supplied UUID, stored as a PostgreSQL UUID.
- Only the owner may retrieve a link's statistics.
- Redirects are public and require no user identity.
- Keep identity extraction replaceable so future authentication can provide
  a verified user ID without changing ownership rules.
- Registration, login, and identity verification are outside scope. The trusted
  header allows impersonation and is a temporary development assumption.

### FR-03: Retain Links and Analytics

- Links do not expire and cannot be deleted through the service in this iteration.
- Retain mappings, ownership, statistics, and all visit logs indefinitely.
- Expiration, configurable lifetimes, and deletion are explicitly outside scope.

### FR-04: Redirect and Record Visits

- Provide `GET /{short_code}` and redirect stored links to their original URLs.
- Count every successful redirect separately, including repeated requests from
  the same IP. Count redirects, not unique visitors or destination-page loads.
- Record the client IP and timestamp for each counted visit.
- Use the direct client address available to the application for now; trusted
  proxy configuration and forwarded-header handling are deferred.
- Unknown links must not redirect or create visit counts or visit logs.
  Ordinary diagnostic/error logging is unaffected.
- Implement reusable visit logging through a decorator or middleware rather
  than duplicating it in endpoint handlers.

### FR-05: Provide Immediate Statistics

- Provide owner-only `GET /stats/{short_code}` returning the link's visit count.
- Keep statistics available to the owner for every stored link.
- Commit visit recording before returning a redirect. A subsequent statistics
  request must see the committed visit.
- Keep the visit log and any separately stored counter consistent in one
  transaction. On recording failure, roll back and return an error without
  redirecting.
- Client receipt of a response is not an additional delivery guarantee; no
  distributed transaction with the browser is required.

## Non-Functional Requirements

- Enforce code uniqueness in PostgreSQL and prevent lost updates during
  concurrent visits. Document transaction boundaries and isolation choices.
- Use database connection pooling and properly manage sessions and transactions.
- Retrieve statistics efficiently and keep redirect/analytics database work small.
  No numerical latency target or throughput benchmark is required.
- Fall back to PostgreSQL if Redis is unavailable. Cache failures must not
  prevent otherwise valid operations, bypass ownership checks, or
  return stale visit counts that violate immediate statistics.
- Explain multi-instance operation, campaign traffic spikes, analytics
  alternatives, and latency/reliability trade-offs in `SCALABILITY.md`.
  Distinguish implemented measures from proposed future scaling work.
- Follow `AGENTS.md`: typed, modular code; Ruff and mypy; pytest unit tests with
  mocked database/cache boundaries. No coverage percentage is required.

## Deliverables and Acceptance

Deliver source code, Alembic migrations, the uv manifest and lockfile, an exported
`requirements.txt`, local startup instructions, a Dockerfile, unit tests,
`SCALABILITY.md`, and supporting design documentation.

Acceptance scenarios must cover independent repeated submissions, ownership,
URL validation, retained links and analytics,
permanent code reservation, collision handling, immediate visit recording,
recording failure without redirect, and Redis failure with PostgreSQL fallback.

## Implementation Decisions and Exclusions

The implementation uses a PostgreSQL sequence encoded as base62, five candidate
attempts, and a unique code primary key. A decorator records visits in one
READ COMMITTED transaction. Redis caches mappings for one hour; failures fall
back to PostgreSQL. Statistics always read PostgreSQL. See entities and flows
for database types, indexing, and transaction details.
Registration/login, expiration, deletion, link editing, custom aliases, raw-log
browsing, and cloud deployment are outside the current scope.
