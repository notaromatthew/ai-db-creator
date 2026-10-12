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
        init_db()
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


from fastapi.responses import JSONResponse, FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        index_file = Path("static/index.html")
        if index_file.exists():
            return FileResponse(index_file)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(router)
app.include_router(progress_router)

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
    return {"status": "ready", "database": "ok"}


from fastapi.staticfiles import StaticFiles

static_dir = Path("static")
if static_dir.exists():
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=int(os.getenv("PORT", settings.port)))
