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
from pathlib import Path

limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

app = FastAPI(title="AI DB Creator", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

app.include_router(router)
app.include_router(progress_router)

@app.on_event("startup")
async def startup():
    Path("uploads").mkdir(parents=True, exist_ok=True)
    Path("projects").mkdir(parents=True, exist_ok=True)
    log.info("AI DB Creator started")

@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "ok"}
