NASA_VALUES = {
    "mental_demand": 50, "physical_demand": 10, "temporal_demand": 40,
    "performance": 80, "effort": 60, "frustration": 30,
}


def test_nasa_raw_tlx_validates_and_aggregates(client, project):
    test_client, _ = client
    response = test_client.post("/api/surveys/nasa-tlx", json={"project_id": project["id"], **NASA_VALUES})
    assert response.status_code == 200
    assert response.json()["aggregate_score"] == 45
    assert test_client.post("/api/surveys/nasa-tlx", json={"project_id": project["id"]}).status_code == 422
    assert test_client.post("/api/surveys/nasa-tlx", json={"project_id": project["id"], **NASA_VALUES, "effort": 101}).status_code == 422
    assert test_client.post("/api/surveys/nasa-tlx", json={**NASA_VALUES}).status_code == 422
    assert test_client.post("/api/surveys/nasa-tlx", json={"project_id": "missing", **NASA_VALUES}).status_code == 404


def test_sus_standard_scoring_and_validation(client, project):
    test_client, _ = client
    response = test_client.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [5, 1] * 5})
    assert response.status_code == 200
    assert response.json()["total_score"] == 100
    assert test_client.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [3] * 9}).status_code == 422
    assert test_client.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [6] * 10}).status_code == 422
