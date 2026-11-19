# URL Shortener

Python 3.14 / FastAPI / SQLModel application with PostgreSQL storage, immediate
visit statistics, and best-effort Redis mapping caching.

## Local setup

Install uv and Python 3.14. Create a dedicated PostgreSQL database and role that
can create tables/sequences, for example through a local PostgreSQL administrator:

```sql
CREATE ROLE shortener LOGIN PASSWORD 'replace-with-local-password';
CREATE DATABASE url_shortener OWNER shortener;
```

Install dependencies and create local configuration:

```sh
uv sync --locked
cp .env.example .env
```

Edit `.env` with your PostgreSQL role/password/database and Redis address.
`DATABASE_URL` and `REDIS_URL` are required, typed connection URLs. Exported
environment variables override `.env`; loading settings does not contact services.
Redis can be unavailable: mapping lookups fall back to PostgreSQL.

```sh
uv run alembic upgrade head
uv run uvicorn url_shortener.main:app --reload --no-proxy-headers
```

Run from the repository root. `GET /health` runs PostgreSQL `SELECT 1`, returning
`200 {"status":"OK"}` or `503` on database failure. It does not check Redis.
API documentation is available at `/docs`.

## Example requests

Create a link using a temporary trusted user UUID:

```sh
curl -i http://127.0.0.1:8000/shorten \
  -H 'Content-Type: application/json' \
  -H 'X-User-ID: 550e8400-e29b-41d4-a716-446655440000' \
  -d '{"original_url":"https://example.com/article"}'
```

Use the returned `short_code` below (the first code in a new database is `1`):

```sh
curl -i http://127.0.0.1:8000/1
curl -i http://127.0.0.1:8000/stats/1 \
  -H 'X-User-ID: 550e8400-e29b-41d4-a716-446655440000'
```

Every creation creates an independent link. Redirects are public and return
`302` with `Cache-Control: no-store`. Each redirect commits its IP/timestamp log
and counter increment before returning. Statistics are owner-only and immediate.
If analytics cannot commit, the request returns `503` without redirecting.
Unknown codes return `404`, other owners receive `403`, and validation failures
return `422`. No expiration, deletion, aliases, or user-account endpoints exist.

**The UUID header is not authentication.** Anyone can supply another UUID.
Real authentication is deliberately deferred. Future verified Google identities
should map to internal application-user UUIDs. Codes are predictable base62
sequence values, not secrets. Destination URLs are syntax-validated but not fetched
or filtered for public-network reachability. All logs, including IPs, are retained.

## Checks and migrations

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run alembic current
uv run alembic check
```

Automated tests mock database/cache boundaries. They are not a throughput benchmark.
To change the schema, update SQLModel tables, generate a candidate with
`uv run alembic revision --autogenerate -m 'Describe schema change'`, review it,
then apply it. Review standalone sequence changes manually. Do not reset the
short-code sequence, reuse codes, or call startup `create_all()`.

Regenerate the assignment's production dependency export after dependency changes:

```sh
uv export --locked --no-dev --no-emit-project --format requirements.txt --output-file requirements.txt
```

## Docker

```sh
docker build -t url-shortener:local .
```

Supply connection URLs reachable **from inside the container**; container localhost
is not your host's PostgreSQL or Redis. An ignored `.env.docker` file can contain
those URLs. On Linux, use `host.docker.internal` with the host-gateway flag below,
provided your host services accept connections on that interface:

```sh
docker run --rm --add-host=host.docker.internal:host-gateway \
  --env-file .env.docker url-shortener:local alembic upgrade head
docker run --rm --add-host=host.docker.internal:host-gateway \
  --env-file .env.docker -p 127.0.0.1:8000:8000 url-shortener:local
```

Migrate once before starting application instances. The image runs as a non-root
user and excludes local credentials. Do not enable reload in a deployed container.
Proxy-aware IP extraction is deferred; startup explicitly disables proxy headers.

## Design and submission

- [Task](Task.md): assignment reference.
- [Requirements](requirements.md), [APIs](apis.md), [entities](entities.md), and
  [flows](flows.md): implemented design and behavioral guarantees.
- [Scalability](SCALABILITY.md): transaction rationale, operational risks, and
  proposed multi-instance/high-traffic architecture.

The submission includes source, migrations, lockfile, `requirements.txt`, Dockerfile,
unit tests, and supporting documentation. Cloud deployment is outside this iteration.

See [VERIFICATION.md](VERIFICATION.md) for executed checks and the current
container-build limitation caused by registry access. When using a mirror,
override the Dockerfile's `PYTHON_IMAGE` build argument with a reachable
Python 3.14-slim image.
