# URL Shortener

Requires Python 3.14 and uv.

Install dependencies and start the development server:

```sh
uv sync --locked
uv run uvicorn url_shortener.main:app --reload
```

Check the health endpoint:

```sh
curl http://127.0.0.1:8000/health
```

Expected response: HTTP 200 with `{"status":"OK"}`. This endpoint reports
application liveness; it does not check PostgreSQL or Redis connectivity.
