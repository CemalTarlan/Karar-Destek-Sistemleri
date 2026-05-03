"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from medsim import __version__
from medsim.api.routes import router
from medsim.config import get_settings
from medsim.llm.client import LMStudioConnectionError
from medsim.schemas.triage import DEFAULT_DISCLAIMER_TR

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="MedSim Triage API",
        version=__version__,
        description=(
            "EĞİTİM ve SİMÜLASYON amaçlı klinik triyaj sistemi. "
            "Gerçek tıbbi tavsiye vermez."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(LMStudioConnectionError)
    async def _lm_studio_handler(_: Request, exc: LMStudioConnectionError) -> JSONResponse:
        logger.error("LM Studio connection error: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "detail": str(exc),
                "hint": (
                    "LM Studio sunucusu çalışıyor mu? "
                    "(Developer sekmesi → Start Server)"
                ),
                "disclaimer": DEFAULT_DISCLAIMER_TR,
            },
        )

    app.include_router(router)
    return app


app = create_app()
