NASA_VALUES = {
    "mental_demand": 50, "physical_demand": 10, "temporal_demand": 40,
    "performance": 80, "effort": 60, "frustration": 30,
}


def test_questionnaires_are_disabled_for_the_current_protocol(client, project):
    from app.config import settings

    test_client, _ = client
    settings.study_questionnaires_enabled = False
    assert test_client.post("/api/surveys/nasa-tlx", json={"project_id": project["id"], **NASA_VALUES}).status_code == 409
    assert test_client.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [5, 1] * 5}).status_code == 409


def test_nasa_raw_tlx_validates_and_aggregates(client, project):
    from app.config import settings

    test_client, _ = client
    settings.study_questionnaires_enabled = True
    try:
        response = test_client.post("/api/surveys/nasa-tlx", json={"project_id": project["id"], **NASA_VALUES})
        assert response.status_code == 200
        assert response.json()["aggregate_score"] == 45
        assert test_client.post("/api/surveys/nasa-tlx", json={"project_id": project["id"]}).status_code == 422
        assert test_client.post("/api/surveys/nasa-tlx", json={"project_id": project["id"], **NASA_VALUES, "effort": 101}).status_code == 422
        assert test_client.post("/api/surveys/nasa-tlx", json={**NASA_VALUES}).status_code == 422
        assert test_client.post("/api/surveys/nasa-tlx", json={"project_id": "missing", **NASA_VALUES}).status_code == 404
    finally:
        settings.study_questionnaires_enabled = False


def test_sus_standard_scoring_and_validation(client, project):
    from app.config import settings

    test_client, _ = client
    settings.study_questionnaires_enabled = True
    try:
        response = test_client.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [5, 1] * 5})
        assert response.status_code == 200
        assert response.json()["total_score"] == 100
        assert test_client.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [3] * 9}).status_code == 422
        assert test_client.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [6] * 10}).status_code == 422
    finally:
        settings.study_questionnaires_enabled = False
