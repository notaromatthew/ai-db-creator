"""Controllo degli accessi ai progetti (task 1.8).

Un solo punto decide chi puo' fare cosa:
- proprietario: tutto, compresa la condivisione e la cancellazione;
- editor: modifica documenti, schema e dati, ma non condivide ne' cancella;
- lettore: vede schema e dati, fa domande in sola lettura, esporta.
L'admin (ruolo Keycloak) gestisce utenti e impostazioni ma non entra nei contenuti altrui.
Un progetto a cui non hai accesso risponde 404, come se non esistesse.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import secrets

from fastapi import Depends

from app.config import settings
from app.core.auth import get_current_user
from app.core.runtime import get_setting
from app.models.database import (
    Project, ProjectInvite, ProjectLink, ProjectMember, User, get_session, init_db,
)
from app.utils.exceptions import AppException

ROLE_RANK = {"viewer": 1, "editor": 2, "owner": 3}
ASSIGNABLE_ROLES = ("viewer", "editor")


@dataclass
class ProjectAccess:
    project_id: str
    role: str
    user_id: str

    def allows(self, minimum: str) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[minimum]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def utcnow_naive() -> datetime:
    # I campi DateTime del modello sono senza fuso: confrontiamo valori UTC "naive".
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_admin(user: dict | None) -> bool:
    return bool(user) and settings.admin_role in (user.get("roles") or [])


def ensure_user(user: dict) -> User:
    """Crea o aggiorna la riga utente e trasforma gli inviti in sospeso in appartenenze."""
    session = get_session(init_db())
    try:
        uid = user.get("sub")
        if not uid:
            raise AppException(detail="Utente non valido", status_code=401)
        row = session.get(User, uid)
        email = (user.get("email") or "").strip().lower() or None
        now = utcnow_naive()
        if row is None:
            row = User(id=uid, email=email, display_name=user.get("name") or user.get("username"),
                       created_at=now, last_seen_at=now)
            session.add(row)
        else:
            row.last_seen_at = now
            if email and row.email != email:
                row.email = email
        trusted = bool(user.get("email_verified")) or not settings.enable_auth or not get_setting("invites_require_verified_email")
        if email and trusted:
            pending = session.query(ProjectInvite).filter(
                ProjectInvite.email == email, ProjectInvite.accepted_at.is_(None),
                ProjectInvite.expires_at > now).all()
            for invite in pending:
                exists = session.query(ProjectMember).filter_by(
                    project_id=invite.project_id, user_id=uid).first()
                if not exists:
                    session.add(ProjectMember(project_id=invite.project_id, user_id=uid,
                                              role=invite.role, invited_by=invite.invited_by))
                invite.accepted_at = now
        session.commit()
        if row.blocked:
            raise AppException(detail="Account sospeso", status_code=403)
        return row
    finally:
        session.close()


def resolve_role(project_id: str, user_id: str) -> str | None:
    session = get_session(init_db())
    try:
        project = session.get(Project, project_id)
        if project is None:
            return None
        if project.owner_id == user_id:
            return "owner"
        member = session.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
        return member.role if member else None
    finally:
        session.close()


def _require(minimum: str):
    def dependency(project_id: str, user: dict = Depends(get_current_user)) -> ProjectAccess:
        row = ensure_user(user)
        role = resolve_role(project_id, row.id)
        if role is None:
            raise AppException(detail="Project not found", status_code=404)
        access = ProjectAccess(project_id=project_id, role=role, user_id=row.id)
        if not access.allows(minimum):
            raise AppException(detail="Permesso insufficiente per questa azione", status_code=403)
        return access
    return dependency


project_viewer = _require("viewer")
project_editor = _require("editor")
project_owner = _require("owner")


def current_app_user(user: dict = Depends(get_current_user)) -> User:
    return ensure_user(user)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not is_admin(user):
        raise AppException(detail="Riservato agli amministratori", status_code=403)
    ensure_user(user)
    return user


def link_project_id(token: str) -> str:
    """Risolve un link pubblico valido (non scaduto, non revocato) nell'id del progetto."""
    session = get_session(init_db())
    try:
        link = session.query(ProjectLink).filter_by(token_hash=hash_token(token)).first()
        if link is None or link.revoked_at is not None or link.expires_at <= utcnow_naive():
            raise AppException(detail="Link non valido", status_code=404)
        return link.project_id
    finally:
        session.close()
