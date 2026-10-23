from fastapi.testclient import TestClient
from app.main import app
from app.services.expert_evaluation_service import expert_service
import pytest

client = TestClient(app)


def test_list_expert_schemas():
    response = client.get("/api/expert/schemas")
    assert response.status_code == 200
    schemas = response.json()
    assert len(schemas) == 30
    assert any(s["code"] == "S01" for s in schemas)
    assert any(s["code"] == "S30" for s in schemas)
    s1 = next(s for s in schemas if s["code"] == "S01")
    assert s1["table_count"] > 0
    assert "tables" in s1
    assert "raw_markdown" in s1
    # Condition and dataset must NOT be present in blind review schemas
    assert "condition" not in s1
    assert "dataset" not in s1


def test_get_single_expert_schema():
    response = client.get("/api/expert/schemas/S01")
    assert response.status_code == 200
    schema = response.json()
    assert schema["code"] == "S01"
    assert len(schema["tables"]) > 0

    response_404 = client.get("/api/expert/schemas/S999")
    assert response_404.status_code == 404


def test_submit_expert_evaluation():
    payload = {
        "evaluator_name": "TestExpert_Alpha",
        "schema_code": "S01",
        "d1_3nf": 5,
        "d2_naming": 4,
        "d3_constraints": 5,
        "d4_relationships": 4,
        "d5_domain": 5,
        "comment": "Ottima decomposizione e consistenza nei vincoli.",
    }
    response = client.post("/api/expert/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "saved"
    assert data["evaluator_name"] == "TestExpert_Alpha"
    assert data["schema_code"] == "S01"

    # Verify listing with evaluator_name marks schema as evaluated
    schemas_resp = client.get("/api/expert/schemas?evaluator_name=TestExpert_Alpha")
    assert schemas_resp.status_code == 200
    s1 = next(s for s in schemas_resp.json() if s["code"] == "S01")
    assert s1["has_evaluated"] is True
    assert s1["rating"]["d1_3nf"] == 5

    # Verify get_my_evaluations
    my_evals = client.get("/api/expert/evaluations/my?evaluator_name=TestExpert_Alpha")
    assert my_evals.status_code == 200
    assert len(my_evals.json()) >= 1


def test_submit_expert_evaluation_validation_error():
    # Value > 5
    invalid_payload = {
        "evaluator_name": "TestExpert_Alpha",
        "schema_code": "S01",
        "d1_3nf": 6,
        "d2_naming": 4,
        "d3_constraints": 5,
        "d4_relationships": 4,
        "d5_domain": 5,
    }
    response = client.post("/api/expert/evaluations", json=invalid_payload)
    assert response.status_code == 422


def test_admin_verify_and_dashboard():
    # Invalid password
    verify_bad = client.post("/api/admin/verify", json={"admin_key": "wrong_key"})
    assert verify_bad.status_code == 401

    # Valid password
    verify_good = client.post("/api/admin/verify", json={"admin_key": "admin123"})
    assert verify_good.status_code == 200
    assert verify_good.json()["valid"] is True

    # Unauthorized dashboard request
    dash_unauth = client.get("/api/admin/expert-evaluations")
    assert dash_unauth.status_code == 401

    # Authorized dashboard request
    dash_auth = client.get("/api/admin/expert-evaluations", headers={"X-Admin-Key": "admin123"})
    assert dash_auth.status_code == 200
    dash_data = dash_auth.json()
    assert dash_data["total_schemas"] == 30
    assert "condition_comparison" in dash_data
    assert "baseline" in dash_data["condition_comparison"]
    assert "full_llm" in dash_data["condition_comparison"]
    assert "dataset_comparison" in dash_data
    assert "evaluator_progress" in dash_data

    # Export CSV
    export_resp = client.get("/api/admin/expert-evaluations/export", headers={"X-Admin-Key": "admin123"})
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers["content-type"]
    assert "evaluator,code,dataset,condition" in export_resp.text
