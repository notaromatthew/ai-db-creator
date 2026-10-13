from fastapi import Depends

from app.config import settings
from app.utils.exceptions import AppException


def require_research():
    """Le funzioni di studio esistono solo con RESEARCH_MODE acceso; altrimenti 404."""
    if not settings.research_mode:
        raise AppException(detail="Not found", status_code=404)
