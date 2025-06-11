# middleware/exception_middleware.py
from prometheus_client import Counter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import time
from ..settings.logger import LoggerFactory

http_requests_total = Counter("http_requests", "Total HTTP requests", ["path"])


class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.log = LoggerFactory

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)

        http_requests_total.labels(path=request.url.path).inc()

        url = request.url
        self.log.log(
            channel="http",
            message=url,
            extra={"duration": time.time() - start, "method": request.method},
        )
        return response
