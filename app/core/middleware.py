import time
import uuid

import structlog
from fastapi import FastAPI, Request

log = structlog.get_logger("app.request")


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=str(uuid.uuid4()), method=request.method, path=request.url.path
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("request_failed")
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info("request_finished", status_code=response.status_code, duration_ms=duration_ms)
        return response
