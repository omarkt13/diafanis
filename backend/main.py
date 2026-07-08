import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diafanis")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"error": {"message": "Internal server error"}})

    from database import Base, engine, SessionLocal
    import models  # noqa: F401  (registers ORM models on Base.metadata)

    Base.metadata.create_all(bind=engine)

    if not _is_test_runtime():
        from seed_data.seed import seed_if_empty

        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()

        from apscheduler.schedulers.background import BackgroundScheduler
        from services.refresh import run_refresh_job, run_startup_catchup

        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(run_refresh_job, "cron", hour=6, minute=0, id="daily_refresh")
        # Catch-up shortly after boot so a cold start (or missed cron) still
        # yields fresh metrics without blocking startup.
        scheduler.add_job(run_startup_catchup, "date", id="startup_catchup")
        scheduler.start()

    from routers.admin import router as admin_router
    from routers.browse import router as browse_router

    app.include_router(browse_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "app": settings.app_name}

    if STATIC_DIR.exists():
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            candidate = STATIC_DIR / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
