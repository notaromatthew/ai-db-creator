import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_is_public_and_has_three_examples():
    r = client.get("/api/examples")
    assert r.status_code == 200
    names = [e["name"] for e in r.json()["examples"]]
    assert names == ["library", "university", "hospital"]
    assert "max-age" in r.headers["cache-control"]


@pytest.mark.parametrize("name,tables", [("library", 5), ("university", 3), ("hospital", 8)])
def test_detail_has_schema_prompt_sources_and_data(name, tables):
    body = client.get(f"/api/examples/{name}").json()
    assert len(body["schema"]["tables"]) == tables
    assert body["prompt"]
    assert body["intro"] and body["choices"]
    assert body["sources"]
    assert [d["table"] for d in body["data"]] == [t["name"] for t in body["schema"]["tables"]]
    assert all(len(d["rows"]) <= 20 and d["total"] >= len(d["rows"]) for d in body["data"])


def test_unknown_name_is_404():
    assert client.get("/api/examples/nope").status_code == 404
    assert client.get("/api/examples/..%2F..%2Fetc").status_code == 404


def test_download_only_listed_source_files():
    ok = client.get("/api/examples/university/files/enrollments.csv")
    assert ok.status_code == 200
    assert client.get("/api/examples/university/files/ground_truth.db").status_code == 404
    assert client.get("/api/examples/university/files/..%2Fprompt.txt").status_code == 404
