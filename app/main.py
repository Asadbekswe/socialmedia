from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import register_request_logging
from app.exceptions.handlers import register_exception_handlers


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="Mini Social Network", version="0.1.0")

    register_request_logging(app)
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app


app = create_app()
