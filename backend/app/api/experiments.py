from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import authenticated_user_id, require_owned_project
from app.core.auth import get_current_user
from app.services.experiment_service import experiment_service
from app.config import settings

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


def require_experiment_mode():
    if not settings.experiment_mode:
        raise HTTPException(status_code=404, detail="Experiment mode disabled")


class StartExperiment(BaseModel):
    project_id: str
    protocol_version: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    duration_minutes: int = Field(default=45, ge=1, le=240)


@router.post("/sessions")
def start_session(payload: StartExperiment, user: dict = Depends(get_current_user)):
    require_experiment_mode()
    require_owned_project(payload.project_id, user)
    return experiment_service.start(authenticated_user_id(user), payload.project_id,
                                    payload.protocol_version, payload.duration_minutes)


@router.get("/sessions/current")
def current_session(user: dict = Depends(get_current_user)):
    require_experiment_mode()
    session = experiment_service.for_subject(authenticated_user_id(user))
    if not session:
        raise HTTPException(status_code=404, detail="Experiment session not found")
    return session


@router.post("/sessions/current/{transition}")
def transition_session(transition: str, user: dict = Depends(get_current_user)):
    require_experiment_mode()
    try:
        return experiment_service.transition(authenticated_user_id(user), transition)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Experiment session not found") from exc
