"""Condivisione dei progetti: membri, inviti per email e link pubblico in sola lettura."""
from datetime import timedelta

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from app.core.acl import (
    ASSIGNABLE_ROLES, ProjectAccess, current_app_user, hash_token, link_project_id,
    new_token, project_owner, project_viewer, utcnow_naive,
)
from app.models.database import (
    AdminAuditLog, Project, ProjectInvite, ProjectLink, ProjectMember, User, get_session, init_db,
)
from app.utils.exceptions import AppException

router = APIRouter(prefix="/api")

def _audit(session, access: ProjectAccess, action: str, detail: dict | None = None):
    """Registro delle modifiche di condivisione: nel dettaglio solo id, mai email salvo quella invitata."""
    session.add(AdminAuditLog(actor_id=access.user_id, action=action, target=access.project_id, detail=detail))


INVITE_DAYS = 14
LINK_DAYS = 30


class InviteRequest(BaseModel):
    email: str
    role: str = "viewer"


class RoleUpdate(BaseModel):
    role: str


def _check_role(role: str) -> str:
    if role not in ASSIGNABLE_ROLES:
        raise AppException(detail="Ruolo non valido: usa viewer o editor", status_code=422)
    return role


@router.get("/projects/{project_id}/sharing")
def get_sharing(project_id: str, access: ProjectAccess = Depends(project_owner)):
    session = get_session(init_db())
    try:
        project = session.get(Project, project_id)
        owner = session.get(User, project.owner_id)
        members = session.query(ProjectMember, User).join(User, User.id == ProjectMember.user_id)\
            .filter(ProjectMember.project_id == project_id).all()
        now = utcnow_naive()
        invites = session.query(ProjectInvite).filter(
            ProjectInvite.project_id == project_id, ProjectInvite.accepted_at.is_(None),
            ProjectInvite.expires_at > now).all()
        links = session.query(ProjectLink).filter(
            ProjectLink.project_id == project_id, ProjectLink.revoked_at.is_(None),
            ProjectLink.expires_at > now).all()
        return {
            "owner": {"id": owner.id, "email": owner.email, "name": owner.display_name},
            "members": [{"user_id": m.user_id, "email": u.email, "name": u.display_name, "role": m.role}
                        for m, u in members],
            "invites": [{"id": i.id, "email": i.email, "role": i.role, "expires_at": i.expires_at.isoformat()}
                        for i in invites],
            "links": [{"id": l.id, "expires_at": l.expires_at.isoformat()} for l in links],
        }
    finally:
        session.close()


@router.post("/projects/{project_id}/invites")
def invite(project_id: str, body: InviteRequest, access: ProjectAccess = Depends(project_owner)):
    role = _check_role(body.role)
    email = body.email.strip().lower()
    if "@" not in email:
        raise AppException(detail="Email non valida", status_code=422)
    session = get_session(init_db())
    try:
        project = session.get(Project, project_id)
        existing = session.query(User).filter(User.email == email).first()
        if existing is not None:
            if existing.id == project.owner_id:
                raise AppException(detail="Questa persona e' gia' la proprietaria", status_code=409)
            member = session.query(ProjectMember).filter_by(project_id=project_id, user_id=existing.id).first()
            if member:
                member.role = role
                _audit(session, access, "share.role_change", {"user_id": existing.id, "role": role})
            else:
                session.add(ProjectMember(project_id=project_id, user_id=existing.id, role=role,
                                          invited_by=access.user_id))
                _audit(session, access, "share.invite", {"email": email, "role": role, "user_id": existing.id})
            session.commit()
            return {"status": "shared", "email": email, "role": role}
        token = new_token()
        session.add(ProjectInvite(project_id=project_id, email=email, role=role, token_hash=hash_token(token),
                                  invited_by=access.user_id, expires_at=utcnow_naive() + timedelta(days=INVITE_DAYS)))
        _audit(session, access, "share.invite", {"email": email, "role": role})
        session.commit()
        return {"status": "shared", "email": email, "role": role}
    finally:
        session.close()


@router.put("/projects/{project_id}/members/{user_id}")
def update_member(project_id: str, user_id: str, body: RoleUpdate, access: ProjectAccess = Depends(project_owner)):
    role = _check_role(body.role)
    session = get_session(init_db())
    try:
        member = session.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
        if member is None:
            raise AppException(detail="Membro non trovato", status_code=404)
        member.role = role
        _audit(session, access, "share.role_change", {"user_id": user_id, "role": role})
        session.commit()
        return {"user_id": user_id, "role": role}
    finally:
        session.close()


@router.delete("/projects/{project_id}/members/{user_id}")
def remove_member(project_id: str, user_id: str, access: ProjectAccess = Depends(project_owner)):
    session = get_session(init_db())
    try:
        member = session.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
        if member is None:
            raise AppException(detail="Membro non trovato", status_code=404)
        session.delete(member)
        _audit(session, access, "share.member_remove", {"user_id": user_id})
        session.commit()
        return {"removed": user_id}
    finally:
        session.close()


@router.delete("/projects/{project_id}/invites/{invite_id}")
def revoke_invite(project_id: str, invite_id: str, access: ProjectAccess = Depends(project_owner)):
    session = get_session(init_db())
    try:
        row = session.query(ProjectInvite).filter_by(id=invite_id, project_id=project_id).first()
        if row is None:
            raise AppException(detail="Invito non trovato", status_code=404)
        session.delete(row)
        _audit(session, access, "share.invite_revoke", {"invite_id": invite_id})
        session.commit()
        return {"revoked": invite_id}
    finally:
        session.close()


@router.delete("/projects/{project_id}/membership")
def leave_project(project_id: str, access: ProjectAccess = Depends(project_viewer)):
    if access.role == "owner":
        raise AppException(detail="Il proprietario non puo' lasciare il progetto", status_code=409)
    session = get_session(init_db())
    try:
        session.query(ProjectMember).filter_by(project_id=project_id, user_id=access.user_id).delete()
        _audit(session, access, "share.leave", {"user_id": access.user_id})
        session.commit()
        return {"left": project_id}
    finally:
        session.close()


@router.post("/projects/{project_id}/links")
def create_link(project_id: str, access: ProjectAccess = Depends(project_owner)):
    token = new_token()
    session = get_session(init_db())
    try:
        session.add(ProjectLink(project_id=project_id, token_hash=hash_token(token), created_by=access.user_id,
                                expires_at=utcnow_naive() + timedelta(days=LINK_DAYS)))
        _audit(session, access, "link.create", {"expires_in_days": LINK_DAYS})
        session.commit()
        # Il token in chiaro si mostra una sola volta: nel database resta solo l'hash.
        return {"token": token, "path": f"/app/shared/{token}", "expires_in_days": LINK_DAYS}
    finally:
        session.close()


@router.delete("/projects/{project_id}/links/{link_id}")
def revoke_link(project_id: str, link_id: str, access: ProjectAccess = Depends(project_owner)):
    session = get_session(init_db())
    try:
        row = session.query(ProjectLink).filter_by(id=link_id, project_id=project_id).first()
        if row is None:
            raise AppException(detail="Link non trovato", status_code=404)
        row.revoked_at = utcnow_naive()
        _audit(session, access, "link.revoke", {"link_id": link_id})
        session.commit()
        return {"revoked": link_id}
    finally:
        session.close()


@router.get("/shared/{token}")
def read_shared(token: str):
    """Vista pubblica in sola lettura: nome e schema, senza autenticazione."""
    project_id = link_project_id(token)
    session = get_session(init_db())
    try:
        project = session.get(Project, project_id)
        if project is None:
            raise AppException(detail="Link non valido", status_code=404)
        return {"name": project.name, "schema": project.schema_json, "read_only": True}
    finally:
        session.close()


@router.get("/me")
def me(user: User = Depends(current_app_user)):
    from app.core.acl import is_admin  # noqa: F401  (il ruolo admin arriva dal token)
    return {"id": user.id, "email": user.email, "name": user.display_name}
