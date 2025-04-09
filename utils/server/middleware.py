# middleware/exception_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import time
from ..settings.logger import LoggerFactory


class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.log = LoggerFactory

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        url = request.url
        self.log.debug(
            name="http",
            message=url,
            extra={"duration": time.time() - start, "method": request.method},
        )
        return response
