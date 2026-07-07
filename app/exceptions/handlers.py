import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.exceptions.base import AppException

log = structlog.get_logger("app")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        log.warning(
            "app_exception",
            type=type(exc).__name__,
            detail=exc.detail,
            status_code=exc.status_code,
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        log.error("db_integrity_error", error=str(exc.orig))
        return JSONResponse(status_code=409, content={"detail": "Conflicting data"})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
