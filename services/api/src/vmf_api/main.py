from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vmf_api import __version__
from vmf_api.api.router import api_router
from vmf_api.api.routes.health import router as health_router
from vmf_api.core.config import get_settings
from vmf_api.core.errors import ConflictError, NotFoundError, RuleValidationError


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Admin-Key",
            "X-Admin-Actor",
        ],
    )

    @application.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(error)},
        )

    @application.exception_handler(ConflictError)
    async def handle_conflict(_: Request, error: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(error)},
        )

    @application.exception_handler(RuleValidationError)
    async def handle_rule_error(_: Request, error: RuleValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(error)},
        )

    application.include_router(health_router)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
