"""API di amministrazione. L'admin vede metadati e consumi, mai il contenuto dei progetti altrui."""
from fastapi import APIRouter, Body, Depends
from sqlalchemy import func

from app.config import settings
from app.core.acl import require_admin, utcnow_naive
from app.core.quota import count_today, user_limit
from app.core.runtime import all_settings, set_setting
from app.models.database import AdminAuditLog, Project, UsageEvent, User, get_session, init_db
from app.utils.exceptions import AppException

router = APIRouter(prefix="/api")


@router.get("/config")
def public_config():
    """Configurazione pubblica per il frontend: nessun segreto."""
    from app.core.runtime import get_setting
    return {
        "research_mode": settings.research_mode,
        "auth_enabled": settings.enable_auth,
        "keycloak_url": settings.keycloak_url,
        "keycloak_realm": settings.keycloak_realm,
        "keycloak_client_id": settings.keycloak_client_id,
        "registration_open": bool(get_setting("registration_open")) and settings.keycloak_allow_registration,
        "maintenance_message": get_setting("maintenance_message"),
    }


def _audit(session, actor: dict, action: str, target: str | None = None, detail: dict | None = None):
    session.add(AdminAuditLog(actor_id=actor.get("sub"), action=action, target=target, detail=detail))


@router.get("/admin/overview")
def overview(admin: dict = Depends(require_admin)):
    session = get_session(init_db())
    try:
        return {
            "users": session.query(User).count(),
            "projects": session.query(Project).count(),
            "ai_calls_today": count_today(),
            "daily_budget": all_settings()["daily_ai_budget_total"],
            "research_mode": settings.research_mode,
            "llm_provider": settings.llm_provider,
        }
    finally:
        session.close()


@router.get("/admin/users")
def list_users(admin: dict = Depends(require_admin)):
    session = get_session(init_db())
    try:
        counts = dict(session.query(Project.owner_id, func.count(Project.id)).group_by(Project.owner_id).all())
        usage = dict(session.query(UsageEvent.user_id, func.count(UsageEvent.id)).group_by(UsageEvent.user_id).all())
        out = []
        for u in session.query(User).order_by(User.created_at.desc()).all():
            out.append({"id": u.id, "email": u.email, "name": u.display_name, "blocked": u.blocked,
                        "projects": counts.get(u.id, 0), "ai_calls_total": usage.get(u.id, 0),
                        "daily_quota": user_limit(u), "custom_quota": u.daily_ai_quota is not None,
                        "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None})
        return out
    finally:
        session.close()


@router.put("/admin/users/{user_id}")
def update_user(user_id: str, blocked: bool | None = Body(None), daily_quota: int | None = Body(None),
                reset_quota: bool = Body(False), admin: dict = Depends(require_admin)):
    session = get_session(init_db())
    try:
        user = session.get(User, user_id)
        if user is None:
            raise AppException(detail="Utente non trovato", status_code=404)
        if user_id == admin.get("sub") and blocked:
            raise AppException(detail="Non puoi sospendere te stesso", status_code=409)
        changes = {}
        if blocked is not None:
            user.blocked = blocked
            changes["blocked"] = blocked
        if reset_quota:
            user.daily_ai_quota = None
            changes["daily_quota"] = "default"
        elif daily_quota is not None:
            if daily_quota < 0:
                raise AppException(detail="Quota non valida", status_code=422)
            user.daily_ai_quota = daily_quota
            changes["daily_quota"] = daily_quota
        _audit(session, admin, "user.update", user_id, changes)
        session.commit()
        return {"id": user_id, **changes}
    finally:
        session.close()


@router.get("/admin/settings")
def get_admin_settings(admin: dict = Depends(require_admin)):
    return all_settings()


@router.put("/admin/settings")
def put_admin_settings(values: dict = Body(...), admin: dict = Depends(require_admin)):
    applied = {}
    for key, value in values.items():
        try:
            applied[key] = set_setting(key, value, admin.get("sub"))
        except (KeyError, ValueError, TypeError):
            raise AppException(detail=f"Impostazione non valida: {key}", status_code=422)
    session = get_session(init_db())
    try:
        _audit(session, admin, "settings.update", None, applied)
        session.commit()
    finally:
        session.close()
    return applied


@router.get("/admin/usage")
def usage(days: int = 14, admin: dict = Depends(require_admin)):
    from datetime import timedelta
    since = utcnow_naive() - timedelta(days=max(1, min(days, 90)))
    session = get_session(init_db())
    try:
        rows = session.query(func.date(UsageEvent.created_at), UsageEvent.kind, func.count(UsageEvent.id))\
            .filter(UsageEvent.created_at >= since).group_by(func.date(UsageEvent.created_at), UsageEvent.kind).all()
        return [{"day": str(d), "kind": k, "count": c} for d, k, c in rows]
    finally:
        session.close()


@router.get("/admin/audit")
def audit(limit: int = 100, admin: dict = Depends(require_admin)):
    session = get_session(init_db())
    try:
        rows = session.query(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(min(limit, 500)).all()
        return [{"actor": r.actor_id, "action": r.action, "target": r.target, "detail": r.detail,
                 "at": r.created_at.isoformat()} for r in rows]
    finally:
        session.close()
