# Repository Guidelines

## Project Structure & Module Organization

This solo interview project is a Python 3.14 URL shortener built with FastAPI, SQLModel, and async SQLAlchemy. PostgreSQL provides durable storage; Redis provides caching. Application code lives in `src/url_shortener/`, tests in `tests/`, and Alembic migrations in `migrations/`. Root design documents define requirements, APIs, entities, and flows.

Treat `.agents/`, `.codex/`, `.aws/`, and `.git/` as environment or tool metadata; do not place application code there.

## Build, Test, and Development Commands

Use uv for dependency management. Commit `pyproject.toml` and `uv.lock`; run project tools through `uv run`:

```sh
uv sync --locked             # Install locked dependencies
uv run pytest                # Run unit tests
uv run ruff format .         # Format code
uv run ruff check .          # Lint code
uv run mypy src/             # Check application types
uv run alembic upgrade head  # Apply database migrations
```

Run FastAPI locally with native or containerized PostgreSQL and Redis. Provide an application Dockerfile for eventual Hamravesh deployment; Docker Compose is not required initially. Document exact startup and Docker build commands in `README.md` once their configuration exists. Manage schema changes with Alembic and commit migration files.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` for modules, functions, and variables, and `PascalCase` for classes. Annotate application function parameters and return values. Use Ruff for formatting, linting, and import sorting, and mypy for type checking. Configure both in `pyproject.toml`. Keep modules focused on a single responsibility.

### General Principles
Keep things in one function unless composable or reusable

Validate unknown values once at the boundary that owns them. Pass typed values inward instead of repeated checks and property-existence checks. Do not defensively revalidate values already guaranteed by a schema, constructor, or internal type.

Do not extract single-use helpers preemptively. Inline the logic at the call site unless the helper is reused, hides a genuinely complex boundary, or has a clear independent name that improves the caller.

Before adding complexity for a speculative or vanishingly unlikely race or security edge case, explain the concrete failure mode, likelihood, and complexity cost to the user and get their buy-in. Do not silently expand scope for theoretical robustness.

Avoid try/catch where possible

## Testing Guidelines

Use pytest with `test_*.py` files and `test_<behavior>` functions. Start with unit tests that mock database and cache boundaries; defer real PostgreSQL/Redis integration tests. Cover important behavior, boundary conditions, failure paths, and bug regressions. No minimum coverage percentage is required.

## Commit Guidelines

Commit directly for this solo project. Keep commits focused and use plain imperative subjects, such as `Add redirect endpoint` or `Fix cache lookup failure`.

## Security & Configuration

Configure connections through `DATABASE_URL` and `REDIS_URL`. Support an ignored local `.env` file, with environment variables taking precedence. Commit `.env.example` with placeholders. Supply deployment configuration through environment variables. Keep credentials and local configuration out of version control.
