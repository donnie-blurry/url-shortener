# Verification

Verified on 2026-11-19 using Python 3.14 and the uv-locked development environment.

## Automated checks

- 62 pytest unit tests passed, using mocked database and cache boundaries.
- Ruff lint and formatting checks passed.
- Strict mypy checks passed for all application modules.
- Offline Alembic SQL generation and Git whitespace checks passed.
- Built the application wheel successfully using the locked, cached build backend.

## Disposable service checks

Used a dedicated PostgreSQL 17 container and Redis container, each with a random
loopback port. Existing laptop services and databases were not modified.

- Applied the initial migration and ran `alembic check` without schema differences.
- Created 20 links concurrently for the same destination; all codes were distinct.
- Ran 50 concurrent redirects for one code; statistics and persisted Visit rows
  both reported exactly 50.
- Verified owner rejection, invalid URL rejection, unknown codes, and real cache fill.
- Forced a Visit insert failure with a temporary database trigger: the redirect
  returned 503, no Location header was sent, and both counter and log totals
  remained 50.
- Repeated a redirect with Redis unavailable: PostgreSQL fallback succeeded and
  statistics immediately increased to 51.
- Downgraded the disposable database to base, upgraded again, and compared schema
  successfully. No throughput or latency benchmark was performed.

## Container verification limit

The Dockerfile parser ran, but the image build could not fetch the Python base
image: public Docker Hub returned 403, and the configured mirror failed DNS
resolution. The image has not been built or runtime-tested in this environment.
Re-run the README Docker build and startup instructions where registry access
is available. `PYTHON_IMAGE` can be overridden with a reachable Python 3.14-slim
mirror using a Docker build argument.
