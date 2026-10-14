import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.routes import router
from app.api.progress import router as progress_router
from app.utils.logger import log
from app.utils.exceptions import AppException, NotFoundException, ValidationException, LLMException, ParsingException
from app.config import settings
from pathlib import Path

limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

from app.core.keycloak_setup import setup_keycloak_realm
from app.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("uploads").mkdir(parents=True, exist_ok=True)
    Path("projects").mkdir(parents=True, exist_ok=True)
    try:
        engine = init_db()
        from app.models.database import run_migrations
        run_migrations(engine)
    except Exception as exc:
        log.error(f"Database initialisation failed at startup: {exc}")
    try:
        await setup_keycloak_realm()
    except Exception as exc:
        log.warning(f"Keycloak realm setup failed at startup: {exc}")
    log.info("AI DB Creator started with PostgreSQL & Keycloak support")
    yield


app = FastAPI(title="AI DB Creator", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Il token dei link condivisi sta nell'URL: niente Referer verso altri siti e niente cache sulle risposte condivise."""
    response = await call_next(request)
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/shared"):
        response.headers["Cache-Control"] = "no-store"
    return response


from fastapi.responses import JSONResponse, FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    path = request.url.path
    is_api = path == "/api" or path.startswith("/api/")
    if exc.status_code == 404 and not is_api and request.method in ("GET", "HEAD"):
        index_file = Path("static/index.html")
        if index_file.exists():
            return FileResponse(index_file)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(router)
app.include_router(progress_router)
from app.api.sharing import router as sharing_router
app.include_router(sharing_router)
from app.api.admin import router as admin_router
app.include_router(admin_router)
from app.api.examples import router as examples_router
app.include_router(examples_router)
from app.api import benchmark_runs, study; app.include_router(benchmark_runs.router); app.include_router(study.router)

@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "ok"}

@app.get("/ready")
@limiter.limit("60/minute")
def ready(request: Request):
    from sqlalchemy import text
    try:
        engine = init_db()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning(f"Readiness check failed: {exc}")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        try:
            import redis
            client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
            try:
                client.ping()
            finally:
                client.close()
        except Exception as exc:
            log.warning(f"Readiness check failed (redis): {type(exc).__name__}")
            return JSONResponse(status_code=503, content={"status": "unavailable", "database": "ok", "redis": "down"})
        return {"status": "ready", "database": "ok", "redis": "ok"}
    return {"status": "ready", "database": "ok"}


from fastapi.staticfiles import StaticFiles

static_dir = Path("static")
if static_dir.exists():
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=int(os.getenv("PORT", settings.port)))
