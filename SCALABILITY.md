# Scalability and Consistency

## Implemented architecture

FastAPI uses SQLModel over async SQLAlchemy/Psycopg. PostgreSQL stores mappings,
UUID ownership, aggregate counts, and every Visit. Redis caches immutable mappings
under `url-shortener:mapping:{code}` for one hour. Cache connection/read timeouts
are 200 ms with no automatic retries. Redis errors fall back to PostgreSQL;
statistics and authorization never use Redis.

Each worker owns one pooled engine and Redis client, closed at shutdown. Each
request receives its own session. PostgreSQL uses READ COMMITTED; pool pre-ping
detects stale connections, and connection establishment has a five-second timeout.
Pool sizes remain SQLAlchemy defaults (five persistent connections, ten overflow
connections per engine). These defaults are starting points, not capacity claims.

## Creation and uniqueness

A shared non-cycling PostgreSQL sequence allocates numbers atomically. Base62
encoding makes short, case-sensitive codes without random collisions in normal
operation. Reserved route names are skipped. The short-code primary key remains
the final authority; only its uniqueness violation triggers a fresh transaction
and another candidate, up to five attempts. Other database errors fail directly.
Sequence values consumed by aborted transactions are not reclaimed. Gaps are
acceptable, and predictability is an explicit trade-off. Never reset the sequence
or independently allocate numbers in application memory. Repeated destination
submissions always create independent mappings and counters.

## Redirect transaction and analytics

A redirect-only decorator opens an explicit transaction around resolution and
visit recording. It uses a database-side `visit_count = visit_count + 1` update
and inserts the IP/timestamp Visit in the same transaction. PostgreSQL serializes
competing updates to the same row, avoiding application-side lost updates. The
foreign key prevents orphan logs. On error both writes roll back when the
transaction outcome is known; no redirect is issued. A commit with an uncertain
outcome is not blindly retried.

The response is released only after commit. A subsequent statistics request reads
the current aggregate in one primary-database lookup, without scanning Visit rows.
Client receipt of a response cannot be made atomic with database commit; a
connection failure after commit can leave a recorded visit without delivery.
We count redirect operations, not destination-page loads or unique visitors.

This approach favors durable immediate statistics over redirect availability
during PostgreSQL outages. Analytics adds database write/commit latency on every
redirect, even on a cache hit. Keep the transaction small and avoid any destination
fetch. Redis cannot eliminate hot-counter contention or PostgreSQL write capacity
limits. No several-thousand-RPS benchmark or numerical latency guarantee is claimed.

## Multiple instances and campaign traffic

The existing shared PostgreSQL sequence, constraints, transactions, and external
Redis work across application instances. No correctness state belongs in process
memory. Place a load balancer before stateless application containers and run
migrations once through a controlled release job before scaling workers.

Budget total database connections across replicas/workers and migration tooling:
with current defaults each engine can open up to 15 connections under load.
Increasing workers without a connection budget can exhaust PostgreSQL. Tune pool
limits, admission control, and potentially PgBouncer from measured traffic.
Scale database storage, WAL/I/O, indexes, and backup/recovery procedures alongside
application capacity; more application replicas cannot fix a single hot counter.

Before a campaign, observe redirect latency, database pool wait, lock wait,
transaction failures, cache hit rate, and Redis timeout rates. Warm known popular
mapping keys, provision headroom, bound request concurrency, and rate-limit abusive
clients at a gateway. A Redis outage sends lookup traffic back to PostgreSQL;
cache stampedes and reconnect storms need capacity planning. Future request
coalescing and TTL jitter can reduce stampedes. Do not cache redirects at a CDN
while claiming every redirect reaches this service's visit counter.

## Analytics alternatives (not implemented)

- A durable outbox plus workers can move processing off the response path while
  preserving event delivery, but stats become delayed and outbox writes still
  involve PostgreSQL. Workers need idempotent processing and duplicate handling.
- A durable queue/stream can decouple analytics throughput; define enqueue failure,
  replay, deduplication, backpressure, and visibility delay before adopting it.
- Background tasks without durable handoff can lose events on process failure.
- Redis counters with periodic database flushing reduce hot-row writes but create
  loss, reconciliation, and freshness trade-offs; they violate current semantics
  unless the requirements change.
- Append-only logs plus batched/sharded counters can improve hot-link throughput
  with more complex aggregation and relaxed freshness.

## Retention, identity, and operations

Unlimited visit retention is implemented. Long-term operation needs storage
forecasting; partitioning and archival are future options, not silent deletion.
The trusted UUID header enables impersonation and must be replaced before offering
real access control. Verified external identity subjects should map to internal
User UUIDs; do not use mutable email addresses as identifiers. Direct-peer IPs are
recorded now. Deployment behind proxies needs an explicit trusted-proxy policy.
Use platform secrets for connection URLs, migrations with least necessary
privileges, persistent database volumes/backups, and readiness checks against
PostgreSQL. Redis unavailability should not alone remove application instances.
