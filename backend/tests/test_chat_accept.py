from pathlib import Path

import json

from app.services.chat_service import add_message, get_history
from app.models.schema_models import NormalizedSchema
from app.utils.research import stable_hash


def test_chat_accept_creates_database_and_clears_history(client, project, tmp_path):
    test_client, routes = client
    project_id = project["id"]
    add_message(project_id, "user", "Crea un catalogo")
    schema = {
        "tables": [
            {
                "name": "prodotti",
                "columns": [
                    {
                        "name": "id",
                        "data_type": "INTEGER",
                        "is_primary_key": True,
                    }
                ],
            }
        ],
        "relationships": [],
        "description": "Catalogo prodotti",
    }

    response = test_client.post(f"/api/projects/{project_id}/chat-accept", json=schema)

    assert response.status_code == 200
    stored_project = test_client.get(f"/api/projects/{project_id}").json()
    assert stored_project["schema_json"]["tables"][0]["name"] == "prodotti"
    assert stored_project["db_path"]
    assert Path(stored_project["db_path"]).exists()
    assert get_history(project_id) == []
    event = next(
        item for item in routes.interaction_logger.get_events(project_id)
        if item["event_type"] == "schema_accepted"
    )
    assert event["data"]["method"] == "human_in_the_loop_chat_accept"
    normalized_schema = NormalizedSchema(**schema).model_dump()
    assert event["data"]["schema_final_hash"] == stable_hash(normalized_schema)
    artifact = tmp_path / "projects" / project_id / event["data"]["run_artifact"]
    artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert artifact_payload["event_type"] == "schema_accepted"
    assert artifact_payload["schema_final_hash"] == stable_hash(normalized_schema)
    assert artifact_payload["schema_final"]["tables"][0]["name"] == "prodotti"
