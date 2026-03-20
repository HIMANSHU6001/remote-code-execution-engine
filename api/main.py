"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import problems, submissions, submit
from api.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing to do (SQLAlchemy engine is created at import time)
    yield
    # Shutdown: dispose async engine
    from db.base import engine
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="RCE & Online Judge",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(submit.router, tags=["submissions"])
    app.include_router(submissions.router, tags=["submissions"])
    app.include_router(problems.router, tags=["problems"])
    app.include_router(ws_router, tags=["websocket"])

    return app


app = create_app()
