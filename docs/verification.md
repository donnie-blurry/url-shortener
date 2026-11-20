# Verification

Verified on 2026-11-20 with Python 3.14 and the uv-locked environment.
This record describes the current Redis Streams implementation; earlier synchronous
analytics checks no longer define the expected redirect behavior.

## Automated checks

- 79 pytest unit tests passed with mocked database/cache/queue boundaries.
- Ruff lint/format checks and strict mypy checks passed.
- Worker tests cover insert/count atomicity, duplicate no-ops, commit-before-ack,
  pending replay, malformed-event quarantine, missing mappings, recovery, retry
  backoff, acknowledgement transactions, and shutdown during failures.
- API tests cover publishing without analytics writes, cache-hit database avoidance,
  redirect-on-publish-failure, delayed statistics, timestamp/IP capture, and the
  unchanged UUID ownership/creation/health contracts.

## Disposable PostgreSQL/Redis checks

Used fresh PostgreSQL 17 and Redis containers on random loopback ports. Existing
laptop services and application data were not modified.

- Applied migration `0001`, inserted a legacy mapping/Visit with a matching count,
  then applied `0002`. Backfill added event UUIDs without losing existing visits
  or changing counts. Alembic detected no model/schema differences.
- Two redirects with the worker stopped queued two events while the processed
  count remained zero. Starting the worker drained the queue and raised it to two.
- Simulated a lost acknowledgement after a real PostgreSQL commit. Marked the
  pending event abandoned and recovered it with another worker: no double-counting.
  Republishing the same event UUID also left the count unchanged.
- Verified the stored visit timestamp matched the producer timestamp.
- Forced a counter-update failure using a temporary database trigger: the inserted
  Visit rolled back, the aggregate stayed unchanged, and the event remained pending.
  Removing the trigger and retrying persisted exactly one Visit/count increment.
- Invalid payloads and absent mappings moved to the failed stream without count changes.
- A cached redirect succeeded with an unreachable PostgreSQL configuration. A
  Redis outage also preserved the resolved redirect, without recording its analytics.
- Started the actual worker module entry point, consumed a queued event, sent
  SIGTERM, and observed a clean exit. Visit-row totals matched processed counts.
- Downgraded `0002` to `0001`, upgraded again, and compared schema successfully
  without losing the pre-existing visit rows.

These checks exercised application recovery, not Redis persistence across a server
crash. No durability beyond configured Redis persistence or throughput SLA is claimed.

## Container checks

Built `bimebazar-url-shortener:queue-verification` through the default ArvanCloud
Python 3.14-slim mirror. Applied migrations from the rebuilt image against the
same disposable database.

Ran the API image with no worker: a created link redirected while statistics
remained zero. Started a separate worker container from that image and verified
statistics caught up to one. The worker ran as non-root `app`. The worker command
is `python -m url_shortener.worker`; the default command remains Uvicorn.

The README documents ArvanCloud as default and Hamravesh as an alternative. No
production services, cloud deployment, or permanent integration suite were added.

## Directory reorganization checks

Reorganized source into `api/`, `links/`, and `visits/`, leaving engine/config/cache
and application/worker entry points at package root. Moved design documentation
into `docs/`; tests remain flat.

- All 79 existing tests, Ruff checks, and strict mypy checks passed after import updates.
- Generated OpenAPI was identical before/after the move, including operation IDs.
- Offline migration SQL was identical, and the rebuilt image's `alembic check`
  reported no model/schema differences on a migrated disposable database.
- The built wheel includes the new packages and excludes obsolete flat modules.
- Local Markdown links resolve after documentation moves.
- Rebuilt the Docker image via ArvanCloud. Verified API health, creation, redirect
  headers, owner checks, and unknown-code behavior. With the worker stopped,
  statistics stayed at zero; the unchanged worker CLI then processed the event
  and raised the count to one.

The refactor introduced no API contract, schema, queue, or dependency changes.
