import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
settings.database_url = "sqlite:///./test_app.db"

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from app.models.database import init_db

init_db(settings.database_url)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_db = f"sqlite:///{tmp_path}/test_app.db"
    settings.database_url = test_db
    init_db(test_db)


    from app.api import routes
    from app.main import app
    from app.services.backup_service import BackupService
    from app.services.document_service import DocumentService
    from app.services.metrics_service import MetricsService
    from app.services.population_service import PopulationService
    from app.services.query_service import QueryService
    from app.services.schema_service import SchemaService

    routes.schema_svc = SchemaService()
    routes.doc_svc = DocumentService()
    routes.pop_svc = PopulationService()
    routes.query_svc = QueryService()
    routes.metrics_svc = MetricsService()
    routes.backup_svc = BackupService()

    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test-user", "username": "test-user"}

    routes.interaction_logger.persist_path = tmp_path / "projects" / "interactions_store.json"
    routes.interaction_logger.events = []
    with TestClient(app) as test_client:
        yield test_client, routes
    app.dependency_overrides.clear()



@pytest.fixture()
def project(client):
    test_client, _ = client
    response = test_client.post("/api/projects", json={"name": "Ricerca", "prompt": "Test"})
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def xlsx_bytes():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["id", "nome"])
    sheet.append([1, "Ada"])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
