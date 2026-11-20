from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from prometheus_client import CollectorRegistry, Histogram, start_http_server
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from url_shortener.config import Settings

LATENCY_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
HTTP_METHODS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"}
)


@contextmanager
def serve_metrics(settings: Settings, registry: CollectorRegistry) -> Iterator[None]:
    if settings.metrics_port is None:
        yield
        return
    server, thread = start_http_server(
        settings.metrics_port, addr=settings.metrics_host, registry=registry
    )
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class HttpMetricsMiddleware:
    def __init__(self, app: ASGIApp, registry: CollectorRegistry) -> None:
        self.app = app
        self.duration = Histogram(
            "url_shortener_http_request_duration_seconds",
            "Time to send the API response body in seconds.",
            ("method", "route", "status_class"),
            registry=registry,
            buckets=LATENCY_BUCKETS,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        method = scope["method"]
        if method not in HTTP_METHODS:
            method = "OTHER"
        status: int | None = None

        def observe(code: int) -> None:
            route = getattr(scope.get("route"), "path", "other")
            self.duration.labels(method, route, f"{code // 100}xx").observe(
                perf_counter() - started
            )

        async def observe_response(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)
            if (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
                and status is not None
            ):
                observe(status)

        try:
            await self.app(scope, receive, observe_response)
        except Exception:
            if status is None:
                observe(500)
            raise
