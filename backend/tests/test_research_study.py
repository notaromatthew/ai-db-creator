"""Studio con partecipanti: consenso, bracci bilanciati, questionari, eventi anonimi, ritiro e cancellazione (8.x)."""
import csv
import io
import json

import pytest
import sqlalchemy as sa

from app.config import settings
from app.core.auth import get_current_user
from app.main import app
from app.models.database import AdminAuditLog, StudyEvent, StudyParticipant, StudyResponse, get_session, init_db

DEMO = {"age_band": "25-34", "role": "studente", "db_experience": 3, "ai_experience": 4}
TLX = {k: 40 for k in ("mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration")}
SUS = [4, 2, 4, 2, 4, 2, 4, 2, 4, 2]


def as_user(sub="partecipante@esempio.it", roles=()):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": sub if "@" in sub else None, "roles": list(roles), "email_verified": True}


@pytest.fixture()
def study(client):
    c, _ = client
    as_user()
    return c


def enroll(c, **over):
    body = {"consent": True, "consent_version": "1.0", "demographics": DEMO, **over}
    return c.post("/api/study/participants", json=body)


def hdr(p):
    return {"X-Study-Code": p["code"]}


def test_research_mode_off_is_404(client):
    c, _ = client
    as_user()
    settings.research_mode = False
    try:
        assert c.post("/api/study/participants", json={}).status_code == 404
        assert c.get("/api/study/info").status_code == 404
    finally:
        settings.research_mode = True


def test_consent_and_demographics_are_required(study):
    c = study
    assert enroll(c, consent=False).status_code == 422
    assert enroll(c, consent="true").status_code == 422
    assert enroll(c, consent_version="0.1").status_code == 422
    assert enroll(c, demographics={**DEMO, "age_band": "9"}).status_code == 422
    assert enroll(c, demographics={**DEMO, "db_experience": 6}).status_code == 422
    assert enroll(c, demographics={"age_band": "25-34"}).status_code == 422
    assert enroll(c, demographics=None).status_code == 422
    r = enroll(c)
    assert r.status_code == 201
    p = r.json()
    assert p["arm"] in ("manual", "ai_only", "ai_interface") and len(p["code"]) == 11 and p["step"] == "task"


def test_assignment_is_balanced_across_three_arms(study):
    c = study
    arms = [enroll(c).json()["arm"] for _ in range(30)]
    assert {a: arms.count(a) for a in set(arms)} == {"manual": 10, "ai_only": 10, "ai_interface": 10}
    # a ogni giro di tre ci sono tutti i bracci
    for i in range(0, 30, 3):
        assert len(set(arms[i:i + 3])) == 3
    status = c.get("/api/study/info").json()
    assert status["consent_version"] == "1.0"


def test_assignment_rebalances_after_withdrawal(study):
    c = study
    ps = [enroll(c).json() for _ in range(3)]
    gone = ps[0]
    assert c.post(f"/api/study/participants/{gone['participant_id']}/withdraw", headers=hdr(gone)).status_code == 200
    assert enroll(c).json()["arm"] == gone["arm"]


def test_participant_needs_code(study):
    c = study
    p = enroll(c).json()
    url = f"/api/study/participants/{p['participant_id']}"
    assert c.post(f"{url}/state").status_code == 404
    assert c.post(f"{url}/state", json={"code": "SBAGLIATO"}).status_code == 404
    assert c.post(f"{url}/state", headers=hdr(p)).json()["step"] == "task"
    assert c.post(f"{url}/state", json={"code": p["code"].lower()}).status_code == 200


def test_full_path_task_tlx_sus_debrief_in_order(study):
    c = study
    p = enroll(c).json()
    base = f"/api/study/participants/{p['participant_id']}"
    h = hdr(p)
    # non si salta il passo del task
    assert c.post(f"{base}/nasa-tlx", json=TLX, headers=h).status_code == 409
    assert c.post(f"{base}/task/complete", headers=h).json()["step"] == "tlx"
    assert c.post(f"{base}/task/complete", headers=h).status_code == 409
    bad = {**TLX, "effort": 42}
    assert c.post(f"{base}/nasa-tlx", json=bad, headers=h).status_code == 422
    assert c.post(f"{base}/nasa-tlx", json={"effort": 5}, headers=h).status_code == 422
    r = c.post(f"{base}/nasa-tlx", json=TLX, headers=h).json()
    assert r == {"step": "sus", "score": 40.0}
    assert c.post(f"{base}/sus", json={"scores": SUS[:9]}, headers=h).status_code == 422
    assert c.post(f"{base}/sus", json={"scores": [6] * 10}, headers=h).status_code == 422
    assert c.post(f"{base}/sus", json={"scores": SUS}, headers=h).json() == {"step": "debrief", "score": 75.0}
    done = c.post(f"{base}/debrief", json={"comment": "scrivimi a mario@esempio.it"}, headers=h).json()
    assert done["step"] == "done"
    state = c.post(f"{base}/state", headers=h).json()
    assert state["step"] == "done" and state["responses"] == ["debrief", "nasa_tlx", "sus"]
    session = get_session(init_db())
    try:
        assert "mario@esempio.it" not in json.dumps(session.query(StudyResponse).filter_by(kind="debrief").one().data)
        assert session.get(StudyParticipant, p["participant_id"]).completed_at is not None
    finally:
        session.close()


def test_events_are_pseudonymous_and_whitelisted(study):
    c = study
    p = enroll(c).json()
    url = f"/api/study/participants/{p['participant_id']}/events"
    h = hdr(p)
    assert c.post(url, json={"type": "clic_strano"}, headers=h).status_code == 422
    r = c.post(url, json={"type": "help_request", "data": {
        "category": "ambiente", "duration_s": 12, "email": "a@b.it", "user_name": "Ada", "ip": "10.0.0.1",
        "note": "contattami a ada@esempio.it da 192.168.1.20", "nested": {"x": 1}}}, headers=h)
    assert r.status_code == 200
    session = get_session(init_db())
    try:
        ev = session.query(StudyEvent).one()
        assert ev.data == {"category": "ambiente", "duration_s": 12, "note": "contattami a [omesso] da [omesso]"}
        assert "tables" not in ev.data
    finally:
        session.close()
    # nessun dato personale nel database: ne' sub/email dell'utente ne' altro
    engine = init_db()
    with engine.connect() as conn:
        dump = ""
        for table in ("study_participants", "study_events", "study_responses"):
            dump += json.dumps([list(map(str, row)) for row in conn.execute(sa.text(f"SELECT * FROM {table}"))])
    assert "partecipante@esempio.it" not in dump and "esempio.it" not in dump.replace("[omesso]", "")


def test_manual_arm_schema_editor_only_for_manual(study):
    c = study
    schema = {"tables": [
        {"name": "studenti", "columns": [{"name": "id", "type": "integer", "primary_key": True, "nullable": False},
                                         {"name": "corso_id", "type": "INTEGER", "references": "corsi.id"}]},
        {"name": "corsi", "columns": [{"name": "id", "type": "INTEGER", "primary_key": True}]}]}
    seen = set()
    for _ in range(6):
        p = enroll(c).json()
        url = f"/api/study/participants/{p['participant_id']}/schema"
        r = c.put(url, json={**schema, "code": p["code"]})
        if p["arm"] == "manual":
            seen.add("manual")
            assert r.status_code == 200 and len(r.json()["schema_hash"]) == 64
            got = c.post(f"{url}/load", json={"code": p["code"]}).json()
            assert [t["name"] for t in got["tables"]] == ["studenti", "corsi"] and got["tables"][0]["columns"][0]["type"] == "INTEGER"
            assert c.put(url, json={"tables": [{"name": "1 tabella!", "columns": []}]}, headers=hdr(p)).status_code == 422
            assert c.put(url, json={"tables": [{"name": "t", "columns": [{"name": "a", "references": "male"}]}]},
                         headers=hdr(p)).status_code == 422
            assert c.put(url, json={"tables": []}, headers=hdr(p)).status_code == 422
        else:
            assert r.status_code == 409
    assert seen == {"manual"}


def test_withdrawal_erases_everything_but_keeps_balance_row(study):
    c = study
    p = enroll(c).json()
    base = f"/api/study/participants/{p['participant_id']}"
    c.post(f"{base}/events", json={"type": "task_start"}, headers=hdr(p))
    c.post(f"{base}/task/complete", headers=hdr(p))
    c.post(f"{base}/nasa-tlx", json=TLX, headers=hdr(p))
    assert c.post(f"{base}/withdraw", headers=hdr(p)).json() == {"status": "withdrawn"}
    assert c.post(f"{base}/state", json={"code": p["code"]}).status_code == 410
    session = get_session(init_db())
    try:
        row = session.get(StudyParticipant, p["participant_id"])
        assert row.demographics is None and row.withdrawn_at and row.step == "withdrawn"
        assert session.query(StudyEvent).count() == 0 and session.query(StudyResponse).count() == 0
    finally:
        session.close()


def test_researcher_panel_status_export_and_erase_by_code(study):
    c = study
    people = [enroll(c).json() for _ in range(6)]
    for p in people[:2]:
        base = f"/api/study/participants/{p['participant_id']}"
        c.post(f"{base}/events", json={"type": "task_start", "data": {"n": 1}}, headers=hdr(p))
        c.post(f"{base}/task/complete", headers=hdr(p))
        c.post(f"{base}/nasa-tlx", json=TLX, headers=hdr(p))
        c.post(f"{base}/sus", json={"scores": SUS}, headers=hdr(p))
        c.post(f"{base}/debrief", json={}, headers=hdr(p))
    # un partecipante non puo' usare il pannello
    assert c.get("/api/study/admin/status").status_code == 403
    assert c.get("/api/study/admin/export").status_code == 403
    assert c.post("/api/study/admin/erase", json={"code": people[0]["code"]}).status_code == 403
    as_user("ricercatore", ["aidb-researcher"])
    status = c.get("/api/study/admin/status").json()
    assert status["total"] == 6 and status["balanced"] is True
    assert {a["arm"]: a["active"] for a in status["arms"]} == {"manual": 2, "ai_only": 2, "ai_interface": 2}
    assert sum(a["completed"] for a in status["arms"]) == 2

    events = list(csv.DictReader(io.StringIO(c.get("/api/study/admin/export?kind=events").text)))
    assert {"participant_id", "arm", "type", "created_at", "data"} == set(events[0])
    assert {e["type"] for e in events} == {"task_start", "task_end"}
    parts = list(csv.DictReader(io.StringIO(c.get("/api/study/admin/export?kind=participants").text)))
    assert len(parts) == 6 and sum(1 for p in parts if p["sus"] == "75.0") == 2 and "email" not in parts[0]
    assert len(list(csv.DictReader(io.StringIO(c.get("/api/study/admin/export?kind=responses").text)))) == 6
    assert c.get("/api/study/admin/export?kind=altro").status_code == 422
    assert c.get("/api/study/admin/export?kind=events&wrap=1").json()["filename"] == "studio-events.csv"

    victim = people[0]
    assert c.post("/api/study/admin/erase", json={"code": "00000-00000"}).status_code == 404
    out = c.post("/api/study/admin/erase", json={"code": victim["code"].lower()}).json()
    assert out["status"] == "erased" and out["participant_id"] == victim["participant_id"]
    assert all(e["participant_id"] != victim["participant_id"] for e in
               csv.DictReader(io.StringIO(c.get("/api/study/admin/export?kind=events").text)))
    again = c.post("/api/study/admin/erase", json={"code": victim["code"]}).json()
    assert again["already_withdrawn"] is True
    session = get_session(init_db())
    try:
        logs = session.query(AdminAuditLog).filter_by(action="study_participant_erased").all()
        assert len(logs) == 2 and logs[0].target == victim["participant_id"]
    finally:
        session.close()
    after = c.get("/api/study/admin/status").json()
    assert sum(a["withdrawn"] for a in after["arms"]) == 1
