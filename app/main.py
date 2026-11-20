"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from .api import admin, mini
from .db import Base, engine  # noqa: F401 - ensures models are registered on Base.metadata
from . import models  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(title="Academy scope/security test target", version="1.0.0")
    app.include_router(admin)
    app.include_router(mini)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
