"""API routes for RQ1 Expert Schema Evaluations & Admin Dashboard."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.config import settings
from app.services.expert_evaluation_service import expert_service
from app.utils.logger import log

router = APIRouter(prefix="", tags=["Expert Evaluations"])


class EvaluationSubmission(BaseModel):
    evaluator_name: str = Field(..., min_length=1, description="Name or identifier of the expert")
    schema_code: str = Field(..., min_length=2, max_length=10, description="Schema code e.g. S01")
    d1_3nf: int = Field(..., ge=1, le=5, description="3NF Compliance Likert score (1-5)")
    d2_naming: int = Field(..., ge=1, le=5, description="Naming Quality Likert score (1-5)")
    d3_constraints: int = Field(..., ge=1, le=5, description="Constraint Coverage Likert score (1-5)")
    d4_relationships: int = Field(..., ge=1, le=5, description="Relationship Accuracy Likert score (1-5)")
    d5_domain: int = Field(..., ge=1, le=5, description="Domain Alignment Likert score (1-5)")
    comment: Optional[str] = Field(None, description="Optional qualitative comments")


class AdminVerifyRequest(BaseModel):
    admin_key: str = Field(..., description="Administrator secret key or password")


def _check_admin_auth(x_admin_key: Optional[str] = Header(None), admin_key: Optional[str] = Query(None)):
    key = x_admin_key or admin_key
    if not key or not expert_service.verify_admin_key(key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chiave amministratore non valida o non fornita",
        )
    return True


@router.get("/api/expert/schemas")
def list_expert_schemas(evaluator_name: Optional[str] = Query(None)):
    """List all condition-blind schemas for expert evaluation."""
    return expert_service.list_schemas(evaluator_name)


@router.get("/api/expert/schemas/{code}")
def get_expert_schema(code: str, evaluator_name: Optional[str] = Query(None)):
    """Get single condition-blind schema by code (e.g. S01)."""
    schema = expert_service.get_schema(code.upper(), evaluator_name)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema {code} non trovato")
    return schema


@router.get("/api/expert/evaluations/my")
def get_my_evaluations(evaluator_name: str = Query(..., min_length=1)):
    """Get all evaluations already submitted by an evaluator."""
    return expert_service.get_evaluations_by_evaluator(evaluator_name)


@router.post("/api/expert/evaluations")
def submit_expert_evaluation(body: EvaluationSubmission):
    """Submit or update Likert ratings and comments for a schema."""
    try:
        result = expert_service.save_evaluation(
            evaluator_name=body.evaluator_name,
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
def verify_admin(body: AdminVerifyRequest):
    """Verify administrator password/key."""
    valid = expert_service.verify_admin_key(body.admin_key)
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password amministratore errata")
    return {"valid": True, "message": "Autenticazione amministratore riuscita"}


@router.get("/api/admin/expert-evaluations")
def get_admin_dashboard_data(
    x_admin_key: Optional[str] = Header(None),
    admin_key: Optional[str] = Query(None),
):
    """Fetch unblinded evaluations, conditions breakdown, and research metrics."""
    _check_admin_auth(x_admin_key, admin_key)
    return expert_service.get_admin_dashboard_data()


@router.get("/api/admin/expert-evaluations/export")
def export_evaluations_csv(
    x_admin_key: Optional[str] = Header(None),
    admin_key: Optional[str] = Query(None),
):
    """Download evaluations as CSV file."""
    _check_admin_auth(x_admin_key, admin_key)
    csv_data = expert_service.export_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=expert_ratings_export.csv",
            "Cache-Control": "no-cache",
        },
    )
