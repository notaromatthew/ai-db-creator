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


def _serialize_reservations(session):
    """Su Postgres serializza le prenotazioni (le INSERT non committate non sono visibili agli
    altri); su SQLite la INSERT prende gia' il lock di scrittura dell'intero database."""
    if session.get_bind().dialect.name == "postgresql":
        from sqlalchemy import text
        session.execute(text("SELECT pg_advisory_xact_lock(740011)"))


def reserve_ai(user: User, kind: str, project_id: str | None = None) -> str:
    """Prenota atomicamente una chiamata AI: inserisce l'evento, riconta nella stessa transazione e
    annulla se supera il tetto globale o la quota dell'utente. Restituisce l'id dell'evento."""
    if not get_setting("ai_enabled"):
        raise AppException(detail="Le funzioni AI sono temporaneamente sospese dall'amministratore. Riprova piu' tardi.", status_code=503)
    total_limit = get_setting("daily_ai_budget_total")
    limit = user_limit(user)
    start = _today_start()
    session = get_session(init_db())
    try:
        _serialize_reservations(session)
        event = UsageEvent(user_id=user.id, project_id=project_id, kind=kind)
        session.add(event)
        session.flush()
        event_id = event.id
        total = session.query(UsageEvent).filter(UsageEvent.created_at >= start).count()
        if total > total_limit:
            session.rollback()
            raise AppException(detail="Il servizio ha raggiunto il limite giornaliero di richieste AI. Riprova domani.", status_code=429)
        mine = session.query(UsageEvent).filter(UsageEvent.created_at >= start, UsageEvent.user_id == user.id).count()
        if mine > limit:
            session.rollback()
            raise AppException(detail="Hai raggiunto il limite giornaliero di richieste AI. Riprova domani.", status_code=429)
        session.commit()
        return event_id
    finally:
        session.close()


def refund_ai(event_id: str | None):
    """Restituisce una prenotazione quando l'operazione non e' partita."""
    if not event_id:
        return
    session = get_session(init_db())
    try:
        session.query(UsageEvent).filter(UsageEvent.id == event_id).delete()
        session.commit()
    finally:
        session.close()


def consume_ai(kind: str):
    """Dipendenza FastAPI: prenota la quota (atomica) prima di chiamare il modello."""
    def dependency(project_id: str | None = None, user: User = Depends(current_app_user)):
        return reserve_ai(user, kind, project_id)
    return dependency
