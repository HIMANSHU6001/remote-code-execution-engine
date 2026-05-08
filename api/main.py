"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, health, problems, submissions, submit, topics
from api.websocket import router as ws_router
from config.settings import get_allowed_origins


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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

    print(get_allowed_origins())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(submit.router, tags=["submissions"])
    app.include_router(submissions.router, tags=["submissions"])
    app.include_router(problems.router, tags=["problems"], prefix="/problems")
    app.include_router(topics.router, tags=["topics"], prefix="/topics")
    app.include_router(auth.router, tags=["auth"], prefix="/api/auth")
    app.include_router(ws_router, tags=["websocket"])
    app.include_router(health.router, tags=["health"])

    return app


app = create_app()
