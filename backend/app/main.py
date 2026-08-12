from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.routes import router
from app.api.progress import router as progress_router
from app.api.experiments import router as experiment_router
from app.utils.logger import log
from app.utils.exceptions import AppException, NotFoundException, ValidationException, LLMException, ParsingException
from app.core.keycloak_setup import setup_keycloak_realm
from app.models.database import init_db, verify_schema_compatibility
from contextlib import asynccontextmanager
from pathlib import Path
from app.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path("uploads").mkdir(parents=True, exist_ok=True)
    Path("projects").mkdir(parents=True, exist_ok=True)
    engine = init_db()
    verify_schema_compatibility(engine)
    if settings.bootstrap_keycloak:
        await setup_keycloak_realm()
    log.info("AI DB Creator started with PostgreSQL & Keycloak support")
    yield


app = FastAPI(title="AI DB Creator", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
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
app.include_router(experiment_router)

@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "ok"}


@app.get("/ready")
async def readiness():
    try:
        with init_db().connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        dependencies = {"database": "ok", "keycloak": "disabled"}
        if settings.enable_auth:
            import httpx
            url = f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}/.well-known/openid-configuration"
            async with httpx.AsyncClient(verify=True, timeout=3.0) as client:
                response = await client.get(url)
                response.raise_for_status()
            dependencies["keycloak"] = "ok"
        return {"status": "ready", **dependencies}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "dependency": "unavailable"})

from fastapi.staticfiles import StaticFiles

static_dir = Path("static")
if static_dir.exists():
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

