# URL Shortener

Python 3.14 / FastAPI / SQLModel service with PostgreSQL storage, Redis mapping
caching, and best-effort background visit processing through Redis Streams.

## Run with Docker Compose

Copy `.env.compose.example` to `.env.compose` and replace both placeholders with
different passwords. Use a URL-safe PostgreSQL password, for example one generated
by `openssl rand -hex 24`, because it also goes into the application database URL.

```sh
docker compose --env-file .env.compose up --build -d
docker compose --env-file .env.compose ps -a
```

Compose starts PostgreSQL and Redis, applies Alembic migrations, and then starts the
API and two visit workers. A successful migration exits with code 0. Open the [API
docs](http://127.0.0.1:8000/docs) or use the example requests below. Sign in to the
[URL Shortener dashboard](http://127.0.0.1:3000/d/url-shortener/url-shortener) as
`admin` with your Compose Grafana password. Grafana provisions the Prometheus data
source and dashboard automatically.

Send requests across several 15-second scrapes to populate the request and worker
rate charts. HTTP latency measures how long the API takes to send the response.
Worker latency covers individual event processing attempts through acknowledgement
or quarantine. A replay counts as an acknowledged attempt and each retry adds a
separate attempt. The scrape health panel lists each replica.

```sh
docker compose --env-file .env.compose up -d --scale worker=3 worker
docker compose --env-file .env.compose down
```

Prometheus picks up new worker replicas through DNS. `down` retains the PostgreSQL,
Redis, Prometheus, and Grafana volumes. The metrics listeners and Prometheus are
reachable inside the Compose network. The API and Grafana use loopback host ports.
Set `API_HOST_PORT` or `GRAFANA_HOST_PORT` in `.env.compose` if a port is in use.
The Python base image, Redis, Prometheus, and Grafana use ArvanCloud by default.
To use another registry, set `PYTHON_IMAGE`, `POSTGRES_IMAGE`, `REDIS_IMAGE`,
`PROMETHEUS_IMAGE`, or `GRAFANA_IMAGE` in `.env.compose`. For example,
`PYTHON_IMAGE=hub.hamdocker.ir/library/python:3.14-slim` uses Hamravesh for Python.

## Native setup

Install uv and Python 3.14. Use PostgreSQL 13+ and Redis 6.2+. Create a dedicated
PostgreSQL database and role allowed to create tables and sequences:

```sql
CREATE ROLE shortener LOGIN PASSWORD 'replace-with-local-password';
CREATE DATABASE url_shortener OWNER shortener;
```

```sh
uv sync --locked
cp .env.example .env
```

Edit `.env` with your real PostgreSQL and Redis connection URLs. Both are required.
Settings are validated on startup. Exported environment variables override `.env`,
and `.env.example` lists the optional settings and their defaults. Never commit
credentials.

Set `REDIS_KEY_PREFIX` to namespace the mapping cache and both visit streams.
Use the same prefix for the API and workers in each deployment. The default
preserves the existing keys. When switching prefixes, stop publishers on the old
prefix and drain its visit stream before switching the workers. The consumer group is
`visit-writers` within each stream. `REDIS_WORKER_TIMEOUT_SECONDS` must exceed
the worker's one-second blocking read.

Configure Redis with persistent storage, AOF (`appendonly yes`,
`appendfsync everysec`), and `maxmemory-policy noeviction`. For a new standalone
local Redis process, an example is:

```sh
redis-server --appendonly yes --appendfsync everysec --maxmemory-policy noeviction
```

Do not launch that command over an already-running service; configure that service
separately if needed. Application code does not change Redis server settings.
Cache keys have TTLs, but Stream events must not be evicted, expired, or trimmed
before processing. AOF everysec can still lose recent events after a crash.

## Migrate and run

Start with a fresh database. The single initial migration creates both tables
and the short-code sequence. Then run the API and worker separately.

```sh
uv run alembic upgrade head
uv run uvicorn url_shortener.main:app --reload --no-proxy-headers
```

In another terminal, from the repository root:

```sh
uv run python -m url_shortener.worker
```

Both processes use the same `.env`. Multiple workers share consumer group
`visit-writers` with distinct consumer names. SIGINT/SIGTERM stop consumption
and close resources; abandoned pending events are reclaimable after 60 seconds.
`GET /health` tests PostgreSQL using `SELECT 1`, not Redis or worker readiness.
It returns `200 {"status":"OK"}` or `503`; cached redirects may work despite a
failed database health check. Swagger documentation is at `/docs`.

Set `METRICS_PORT` per process to expose Prometheus metrics on a dedicated listener.
When running both processes on the same host, give each a different port.
`METRICS_HOST` defaults to `127.0.0.1`.

```sh
METRICS_PORT=9100 uv run uvicorn url_shortener.main:app --no-proxy-headers
METRICS_PORT=9101 uv run python -m url_shortener.worker
```

Run those commands in separate terminals and scrape `/metrics` on each port.
Use one Uvicorn process per metrics port.

## Example requests

In `/docs`, click **Try it out** and use the **Demo owner** example for
`X-User-ID`. Keep the same UUID for link creation and statistics requests.
To try another owner, generate a UUID with
`uv run python -c 'from uuid import uuid4; print(uuid4())'` and reuse that value.

```sh
curl -i http://127.0.0.1:8000/shorten \
  -H 'Content-Type: application/json' \
  -H 'X-User-ID: 550e8400-e29b-41d4-a716-446655440000' \
  -d '{"original_url":"https://example.com/article"}'
```

Use the returned code below (`1` is the first allocation in a fresh database):

```sh
curl -i http://127.0.0.1:8000/1
curl -i http://127.0.0.1:8000/stats/1 \
  -H 'X-User-ID: 550e8400-e29b-41d4-a716-446655440000'
```

Every creation is independent. Public redirects return `302` with `no-store`.
The decorator attempts to enqueue an event, but publishing failure never blocks
a resolved redirect. Statistics are owner-only and show **processed visits**:
counts can lag while workers are stopped, and failed publishing/persistence can
leave permanent undercounts. Every event that commits is logged and counted in
one transaction. Replays do not increment again. Unknown lookups return `404`,
other owners receive `403`, and invalid inputs return `422`.

**The UUID header is not authentication.** Future verified Google identities
should map to internal user UUIDs. Codes are predictable, not secrets. URLs are
syntax-validated without fetching destinations or filtering private addresses.
Mappings and processed IP/timestamp logs are retained indefinitely. Expiration,
deletion, registration, and login remain outside scope.

## Queue operations

Use your Redis connection URL and the deployment's key prefix to inspect queues.

```sh
redis-cli -u "$REDIS_URL" XLEN "${REDIS_KEY_PREFIX:-url-shortener}:visits"
redis-cli -u "$REDIS_URL" XPENDING "${REDIS_KEY_PREFIX:-url-shortener}:visits" visit-writers
redis-cli -u "$REDIS_URL" XRANGE "${REDIS_KEY_PREFIX:-url-shortener}:visits:failed" - + COUNT 10
```

Shell variables must be exported; the shell does not automatically read `.env`.
The group is created when a worker starts, so XPENDING can report NOGROUP before
that. Monitor backlog, oldest pending age, publishing failures, retries, and the
failed stream. Do not manually acknowledge or delete pending messages to clear
backlog. Failed entries retain their source ID, raw payload, and reason for
inspection. Repair/replay tooling is outside this iteration.

## Checks and schema changes

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run alembic current
uv run alembic check
```

Tests mock database/cache/queue boundaries. For schema changes, update models,
generate a candidate with `uv run alembic revision --autogenerate -m 'Describe change'`,
review it, and apply it. Review standalone sequence changes manually. Do not reset
the short-code sequence or use startup `create_all()`.

Export production dependencies after dependency changes:

```sh
uv export --locked --no-dev --no-emit-project --format requirements.txt --output-file requirements.txt
```

## Docker

```sh
docker build -t url-shortener:local .
```

The default base is `docker.arvancloud.ir/python:3.14-slim`. Hamravesh is also usable:

```sh
docker build --build-arg PYTHON_IMAGE=hub.hamdocker.ir/library/python:3.14-slim \
  -t url-shortener:local .
```

Supply an ignored `.env.docker` with URLs reachable from inside containers.
Container localhost is not your host's database. On Linux, for host services
listening on an appropriate interface, use the host-gateway mapping:

```sh
docker run --rm --add-host=host.docker.internal:host-gateway \
  --env-file .env.docker url-shortener:local alembic upgrade head
docker run --rm --add-host=host.docker.internal:host-gateway \
  --env-file .env.docker -p 127.0.0.1:8000:8000 url-shortener:local
docker run --rm --add-host=host.docker.internal:host-gateway \
  --env-file .env.docker url-shortener:local python -m url_shortener.worker
```

Run migration once, then API and worker as separate containers. The same image
runs both as a non-root user. Credentials are excluded, reload is disabled, and
proxy-aware IP handling is deferred (`--no-proxy-headers`).

## Design and submission

[Task.md](Task.md) is the assignment reference. [Requirements](docs/requirements.md),
[APIs](docs/apis.md), [entities](docs/entities.md), and [flows](docs/flows.md) describe current
behavior. [SCALABILITY.md](SCALABILITY.md) explains loss/freshness trade-offs and
[VERIFICATION.md](docs/verification.md) records executed checks. The submission includes
source, migrations, lockfile, production requirements export, Dockerfile, Compose
configuration, dashboard provisioning, and tests.
Cloud deployment is outside scope.
