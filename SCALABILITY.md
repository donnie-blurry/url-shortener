# Scalability and Consistency

## Implemented architecture

The FastAPI process handles validation, UUID ownership, mapping creation, and
resolution. A separate worker consumes Redis Stream visit events and persists
analytics. PostgreSQL owns mappings and processed Visit/counter data. By default,
Redis caches immutable mappings for one hour and stores queued work in
`url-shortener:visits`.

The API uses separate cache and publisher connections with 200 ms default
connection/read timeouts and no automatic retries. Workers use separate Redis
connections with a default five-second read timeout for one-second blocking
consumer reads. Each process owns an async SQLAlchemy pool and request/task
sessions, closing resources at shutdown.
Use READ COMMITTED and pool pre-ping. Pool defaults permit five persistent plus
ten overflow connections per engine; budget connections across all API and worker
processes. PostgreSQL connection establishment has a default five-second timeout.

## Redirect availability and freshness

A cache hit does not query PostgreSQL. Cache misses close their lookup transaction
before cache fill/publish operations. The redirect decorator creates a UUID event,
capturing the request IP/time, and attempts one publish before returning `302`.
Publishing failure is logged but does not suppress a resolved redirect. Cache
failures fall back to PostgreSQL; if Redis is also the unavailable broker, that
request's analytics may be lost. PostgreSQL outages do not prevent cache-hit
redirects, but creation, statistics, cache misses, and database readiness can fail.

Statistics returns the primary database's committed processed counter in one
lookup, not a Visit scan or a Redis count. It is eventually consistent, with no
freshness SLA: workers being offline causes unbounded lag, while lost events cause
permanent undercounting. Receipt of a redirect cannot be atomic with queue publish.
A publish timeout may have accepted the event, even though the API logs a failure.

## Worker delivery and database effects

All workers share consumer group `visit-writers`, created at ID `0` to include
pre-start events. Each worker reads one event at a time. Every five seconds it
scans pending work with XAUTOCLAIM, using a 60-second idle threshold. A forced
process exit leaves unacknowledged work recoverable. SIGTERM/SIGINT finish the
current attempt when possible, then close resources and stop consumption.

A unique non-null Visit event UUID identifies the logical event across delivery
attempts. The worker inserts with ON CONFLICT DO NOTHING and increments the
ShortLink counter only for a new Visit, in the same PostgreSQL transaction.
Failures roll both changes back. PostgreSQL serializes updates to the same counter,
preventing lost updates. Replayed events, including commit-before-ack crashes,
do not increment again. Preserve producer timestamps rather than worker time.

Commit precedes acknowledgement. XACK and XDEL share a Redis transaction. Database
or Redis failures retain pending work for retry, with exponential delays from one
to 30 seconds. Malformed events and missing mappings move to
`url-shortener:visits:failed`, together with acknowledgement/deletion of the original.
They do not affect counters and are retained for inspection. Delivery can repeat;
only database effects for a retained event UUID are deduplicated. Do not claim
exactly-once delivery or lossless analytics.

Migration `0002` backfills existing visits with UUIDs, enforces uniqueness, and
preserves counts. Stop old API instances before migration/new worker rollout.
Do not mix old direct writers with versions requiring explicit event IDs.

## Redis persistence and backlog

Use Redis 6.2+ with persistent storage, AOF (`appendonly yes`, `appendfsync everysec`),
and `maxmemory-policy noeviction`. Cache entries expire normally, but queued work
must not be expired or trimmed before processing. AOF everysec can lose recent
writes on a crash. No eviction does not prevent publishing failure when memory
is exhausted; the API then redirects without analytics. Streams are not merely
reconstructible cache data: monitor storage and backups as well as availability.

Retaining unprocessed events and failed entries can consume unbounded space during
outages. Monitor stream length, pending count, oldest pending age, failed-stream
length, publishing failures, worker retries, processing throughput, and count lag.
Provision headroom and operational recovery procedures. Cache and queue share Redis
in this iteration; separating their instances is a future way to isolate memory
pressure and persistence policies.

## Creation and multiple instances

The API is expected to be read-heavy because links are typically followed more
often than they are created. Cached redirects avoid PostgreSQL lookups, while
redirect traffic can still generate substantial asynchronous analytics writes.

Every successful submission creates an independent mapping. PostgreSQL enforces
uniqueness through the `short_code` primary key, and creation commits the mapping
before returning it. The application skips reserved names and retries only code
collisions within the `MAX_CODE_ATTEMPTS` budget, which defaults to five candidates.

### Short-code allocation trade-offs

- **PostgreSQL sequence (current).** A shared non-cycling sequence gives concurrent
  API instances distinct numbers. Base62 encoding yields short early codes that
  are easy to enumerate. Failed transactions can leave gaps. The current path
  makes a separate `nextval` call before the insert. PostgreSQL already stores the
  mapping, so it is the only service required for creation.
- **Redis counter.** A per-link `INCR` moves allocation off PostgreSQL, but creation
  still makes two sequential calls and now depends on both services. The resulting
  Base62 codes are still predictable. A Redis crash or failover that rolls back the
  counter can reissue numbers for committed links. PostgreSQL rejects those
  collisions, and creation can exhaust its retries until the counter is repaired.
- **Random Base62.** Generate fixed-length candidates locally with `secrets` and
  use `INSERT ... ON CONFLICT (short_code) DO NOTHING RETURNING ...`. When the
  insert returns no row, draw another candidate within the retry budget. This
  avoids a shared allocator and a separate existence check. Codes are harder to
  guess and longer than early sequence codes. Seven Base62 characters give about
  3.52 trillion possibilities. With 10 million occupied codes of that length,
  about one in 352,000 new draws would collide.

### Batched Redis allocation for higher creation throughput

If sequence allocation becomes a bottleneck as more API instances handle link
creation, each instance could reserve a disjoint range of 1,000 numbers with a
single atomic `INCRBY`. It would consume that range locally and reserve another
when exhausted. This removes per-link PostgreSQL sequence calls and reduces
contention on the Redis counter compared with per-link `INCR`, since a fully
consumed range needs one Redis call per 1,000 allocations. Every link still
requires a PostgreSQL insert and commit. Scaling database write capacity and
handling analytics contention are separate concerns.

Instance restarts can leave gaps when part of a reserved range goes unused. To
switch allocators, stop PostgreSQL sequence allocators before initializing the
Redis counter to at least the sequence's last allocated value. After Redis
counter loss or rollback, stop all allocators, discard outstanding ranges, and
reseed the counter above the highest committed code number before resuming.
PostgreSQL's primary key remains the final uniqueness check.

API and worker instances can scale separately behind a load balancer, sharing
PostgreSQL and the Stream consumer group. Migrate once before rolling processes.
More workers improve distinct-link throughput but do not remove hot-row contention
when a campaign targets one link. Database I/O/WAL, pool waits, lock contention,
and unbounded visit-log growth remain capacity limits. No thousands-RPS benchmark
or numerical latency guarantee is claimed.

Before a campaign, prewarm common mappings, provision API/worker/Redis/PostgreSQL
capacity, measure queue lag, and bound concurrency. A cache outage increases
PostgreSQL lookup traffic; TTL jitter and request coalescing are future stampede
controls. Avoid CDN redirect caching if the goal is to observe every redirect at
this service. Gateway admission control/rate limits and PgBouncer may be justified
by measurements rather than adding workers without a database connection budget.

## Alternatives and limits

- Batching or sharded aggregates could reduce hot-counter contention; not implemented.
- A PostgreSQL outbox could improve handoff durability, but restores a redirect-time
  database write. Current behavior explicitly prefers availability and tolerates loss.
- A dedicated durable broker could separate queue persistence from cache operations.
- Fire-and-forget in-process tasks provide weaker crash recovery than retained Streams.
- Redis-only counters with periodic flushing require additional reconciliation and
  loss semantics; current counts remain PostgreSQL transaction results.

Processed logs and mappings are retained indefinitely. Partitioning/archival and
queue repair tools are future work. Trusted UUID headers enable impersonation;
authentication must eventually map verified external subjects to internal user
UUIDs. Direct-peer IPs are captured now; trusted proxy handling is deferred.
Use platform secrets and persistent PostgreSQL backups. `/health` remains a database
readiness check, not a measure of cached redirect or worker availability.
