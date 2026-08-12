from datetime import datetime, timedelta, timezone

from app.config import settings
from app.core.auth import get_current_user
from app.main import app
from app.services.experiment_service import CAPABILITIES, experiment_service
from app.models.schema_models import NormalizedSchema, TableDef, ColumnDef


def _find_subject(arm: str) -> str:
    for index in range(1000):
        subject=f"e2e-{arm}-{index}"
        key=experiment_service._subject_key(subject)
        if experiment_service._condition(key,"pilot-v1")==arm: return subject
    raise AssertionError("arm not found")


def test_three_arm_api_capabilities_timeout_withdraw_and_recovery(client, monkeypatch, tmp_path):
    test_client, routes=client; monkeypatch.setattr(settings,"experiment_mode",True)
    async def offline_chat(*_args,**_kwargs): return "offline"
    async def offline_extract(*_args,**_kwargs): return None
    schema=NormalizedSchema(tables=[TableDef(name="items",columns=[ColumnDef(name="id",data_type="INTEGER",is_primary_key=True)])],relationships=[])
    async def offline_generate(*_args,**_kwargs): return schema
    async def offline_populate(*_args,**_kwargs): return {"items":{"inserted":0,"skipped":0,"provenance":{"method":"offline_mock"}}}
    monkeypatch.setattr(routes,"chat",offline_chat); monkeypatch.setattr(routes,"extract_schema_with_fallback",offline_extract)
    monkeypatch.setattr(routes.schema_svc,"generate_from_prompt",offline_generate); monkeypatch.setattr(routes.pop_svc,"populate",offline_populate)
    monkeypatch.setattr(experiment_service,"project_eraser",lambda _project_id: None)
    experiment_service.path=tmp_path/"projects"/"experiment_sessions.json"
    for arm in ("manual","ai_only","ai_interface"):
        subject=_find_subject(arm); app.dependency_overrides[get_current_user]=lambda subject=subject:{"sub":subject,"username":subject}
        project=test_client.post("/api/projects",json={"name":arm,"prompt":""}).json(); pid=project["id"]
        session=test_client.post("/api/experiments/sessions",json={"project_id":pid,"protocol_version":"pilot-v1"})
        assert session.status_code==200 and session.json()["condition"]==arm and session.json()["capabilities"]==sorted(CAPABILITIES[arm])
        upload=test_client.post(f"/api/projects/{pid}/documents",files={"file":("source.txt",b"offline fixture","text/plain")})
        assert upload.status_code==200
        generated=test_client.post(f"/api/projects/{pid}/generate",json={"prompt":"offline","document_ids":[]})
        assert generated.status_code==(403 if arm=="manual" else 200)
        routes.schema_svc.update_schema(pid,schema)  # deterministic provider-mock output persisted by the fixture
        populated=test_client.post(f"/api/projects/{pid}/populate",json={"document_ids":[]})
        assert populated.status_code==(403 if arm=="manual" else 200)
        assert test_client.post(f"/api/projects/{pid}/chat",json={"message":"x","document_ids":[]}).status_code==(403 if arm!="ai_interface" else 200)
        edit=test_client.put(f"/api/projects/{pid}/schema",json={"tables":[],"relationships":[]})
        assert edit.status_code==(403 if arm=="ai_only" else 200)
        assert test_client.post("/api/surveys/sus",json={"project_id":pid,"scores":[3]*10}).status_code==200
        assert test_client.get(f"/api/projects/{pid}/export?format=json").status_code==200
        if arm=="manual":
            data=experiment_service._load(); sid=session.json()["session_id"]; data["sessions"][sid]["deadline_at"]=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
            from app.utils.research import atomic_write_json
            atomic_write_json(experiment_service.path,data)
            assert test_client.put(f"/api/projects/{pid}/schema",json={"tables":[],"relationships":[]}).status_code==409
        else:
            assert test_client.post("/api/experiments/sessions/current/withdrawn",json={}).status_code==200
            assert test_client.get(f"/api/projects/{pid}").status_code==403
    # corrupt input does not poison subsequent authenticated requests
    monkeypatch.setattr(settings,"experiment_mode",False)
    app.dependency_overrides[get_current_user]=lambda:{"sub":"recovery","username":"recovery"}
    assert test_client.post("/api/projects",content=b"not-json",headers={"content-type":"application/json"}).status_code==422
    assert test_client.post("/api/projects",json={"name":"recovered","prompt":""}).status_code==200
