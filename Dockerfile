ARG PYTHON_IMAGE=docker.arvancloud.ir/python:3.14-slim
FROM ${PYTHON_IMAGE} AS build
RUN pip install --no-cache-dir uv==0.13.9
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM ${PYTHON_IMAGE}
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
USER app
EXPOSE 8000
CMD ["uvicorn", "url_shortener.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
