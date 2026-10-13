"""Quote di utilizzo AI: per utente al giorno e tetto globale."""
from datetime import timedelta

from fastapi import Depends

from app.core.acl import current_app_user, utcnow_naive
from app.core.runtime import get_setting
from app.models.database import UsageEvent, User, get_session, init_db
from app.utils.exceptions import AppException


def _today_start():
    return utcnow_naive().replace(hour=0, minute=0, second=0, microsecond=0)


def count_today(user_id: str | None = None) -> int:
    session = get_session(init_db())
    try:
        q = session.query(UsageEvent).filter(UsageEvent.created_at >= _today_start())
        if user_id:
            q = q.filter(UsageEvent.user_id == user_id)
        return q.count()
    finally:
        session.close()


def user_limit(user: User) -> int:
    return user.daily_ai_quota if user.daily_ai_quota is not None else get_setting("default_daily_ai_quota")


def consume_ai(kind: str):
    """Dipendenza FastAPI: controlla le quote e registra l'uso prima di chiamare il modello."""
    def dependency(project_id: str | None = None, user: User = Depends(current_app_user)):
        if count_today() >= get_setting("daily_ai_budget_total"):
            raise AppException(detail="Il servizio ha raggiunto il limite giornaliero di richieste AI. Riprova domani.", status_code=429)
        if count_today(user.id) >= user_limit(user):
            raise AppException(detail="Hai raggiunto il limite giornaliero di richieste AI. Riprova domani.", status_code=429)
        session = get_session(init_db())
        try:
            session.add(UsageEvent(user_id=user.id, project_id=project_id, kind=kind))
            session.commit()
        finally:
            session.close()
    return dependency
