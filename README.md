# URL Shortener

Requires Python 3.14 and uv.

Install dependencies:

```sh
uv sync --locked
```

Copy the configuration template and replace the placeholders with your local
PostgreSQL credentials and connection details:

```sh
cp .env.example .env
```

`DATABASE_URL` and `REDIS_URL` are required. Settings load `.env` from the current
working directory; exported environment variables override values in that file.
Keep `.env` local and run commands from the repository root. Loading settings
validates the connection URLs but does not connect to either service.

Start the development server:

```sh
uv run uvicorn url_shortener.main:app --reload
```

Check the health endpoint:

```sh
curl http://127.0.0.1:8000/health
```

Expected response: HTTP 200 with `{"status":"OK"}`. This endpoint reports
application liveness and psql connection
