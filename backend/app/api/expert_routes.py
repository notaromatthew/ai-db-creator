"""API routes for RQ1 Expert Schema Evaluations & Admin Dashboard."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.config import settings
from app.core.auth import get_current_user
from app.services.expert_evaluation_service import expert_service
from app.utils.logger import log

router = APIRouter(prefix="", tags=["Expert Evaluations"])


class EvaluationSubmission(BaseModel):
    evaluator_name: Optional[str] = Field(None, description="Evaluator label; ignored when authentication is enabled")
    schema_code: str = Field(..., min_length=2, max_length=10, description="Schema code e.g. S01")
    d1_3nf: int = Field(..., ge=1, le=5, description="3NF Compliance Likert score (1-5)")
    d2_naming: int = Field(..., ge=1, le=5, description="Naming Quality Likert score (1-5)")
    d3_constraints: int = Field(..., ge=1, le=5, description="Constraint Coverage Likert score (1-5)")
    d4_relationships: int = Field(..., ge=1, le=5, description="Relationship Accuracy Likert score (1-5)")
    d5_domain: int = Field(..., ge=1, le=5, description="Domain Alignment Likert score (1-5)")
    comment: Optional[str] = Field(None, description="Optional qualitative comments")


class AdminVerifyRequest(BaseModel):
    admin_key: str = Field(..., description="Administrator secret key or password")


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _optional_identity(user: dict, requested: Optional[str]) -> Optional[str]:
    if settings.enable_auth:
        return str(user.get("username") or user.get("sub") or "").strip() or None
    return (requested or "").strip() or None


def _evaluator_identity(user: dict, requested: Optional[str]) -> str:
    identity = _optional_identity(user, requested)
    if not identity:
        raise HTTPException(status_code=400, detail="evaluator_name is required")
    return identity


def _check_admin_auth(request: Request, x_admin_key: Optional[str] = Header(None)):
    client = _client_id(request)
    if expert_service.admin_attempts_blocked(client):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Troppi tentativi, riprova piu' tardi")
    if not x_admin_key or not expert_service.verify_admin_key(x_admin_key):
        expert_service.record_admin_failure(client)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chiave amministratore non valida o non fornita",
        )
    expert_service.clear_admin_failures(client)
    return True


@router.get("/api/expert/schemas")
def list_expert_schemas(evaluator_name: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    """List all condition-blind schemas for expert evaluation."""
    return expert_service.list_schemas(_optional_identity(user, evaluator_name))


@router.get("/api/expert/schemas/{code}")
def get_expert_schema(code: str, evaluator_name: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    """Get single condition-blind schema by code (e.g. S01)."""
    schema = expert_service.get_schema(code.upper(), _optional_identity(user, evaluator_name))
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema {code} non trovato")
    return schema


@router.get("/api/expert/evaluations/my")
def get_my_evaluations(evaluator_name: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    """Get all evaluations already submitted by an evaluator."""
    return expert_service.get_evaluations_by_evaluator(_evaluator_identity(user, evaluator_name))


@router.post("/api/expert/evaluations")
def submit_expert_evaluation(body: EvaluationSubmission, user: dict = Depends(get_current_user)):
    """Submit or update Likert ratings and comments for a schema."""
    evaluator = _evaluator_identity(user, body.evaluator_name)
    try:
        result = expert_service.save_evaluation(
            evaluator_name=evaluator,
            schema_code=body.schema_code,
            d1_3nf=body.d1_3nf,
            d2_naming=body.d2_naming,
            d3_constraints=body.d3_constraints,
            d4_relationships=body.d4_relationships,
            d5_domain=body.d5_domain,
            comment=body.comment,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Error submitting expert evaluation: {e}")
        raise HTTPException(status_code=500, detail="Errore nel salvataggio della valutazione")


@router.post("/api/admin/verify")
def verify_admin(body: AdminVerifyRequest, request: Request):
    """Verify administrator password/key."""
    client = _client_id(request)
    if expert_service.admin_attempts_blocked(client):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Troppi tentativi, riprova piu' tardi")
    if not expert_service.verify_admin_key(body.admin_key):
        expert_service.record_admin_failure(client)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password amministratore errata")
    expert_service.clear_admin_failures(client)
    return {"valid": True, "message": "Autenticazione amministratore riuscita"}


@router.get("/api/admin/expert-evaluations")
def get_admin_dashboard_data(request: Request, x_admin_key: Optional[str] = Header(None)):
    """Fetch unblinded evaluations, conditions breakdown, and research metrics."""
    _check_admin_auth(request, x_admin_key)
    return expert_service.get_admin_dashboard_data()


@router.get("/api/admin/expert-evaluations/export")
def export_evaluations_csv(request: Request, x_admin_key: Optional[str] = Header(None)):
    """Download evaluations as CSV file."""
    _check_admin_auth(request, x_admin_key)
    csv_data = expert_service.export_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=expert_ratings_export.csv",
            "Cache-Control": "no-cache",
        },
    )
