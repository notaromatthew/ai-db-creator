import asyncio

from app.evaluation import llm_adjudication as adj
from app.models.schema_models import NormalizedSchema, TableDef, ColumnDef


def _schema():
    return NormalizedSchema(tables=[TableDef(name="students", columns=[
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
        ColumnDef(name="name", data_type="TEXT"),
    ])], relationships=[])


def test_dump_schema_lists_columns_and_constraints():
    schema = _schema()
    out = adj._dump_schema(schema)
    assert "students" in out
    assert "id INTEGER PK" in out
    assert "name TEXT" in out


def test_rows_to_text_limits_and_tags_empty():
    assert adj._rows_to_text("t", [], limit=5) == "t: (empty)"
    assert adj._rows_to_text("t", [], limit=12) == "t: (empty)"


def test_adjudicate_parses_scores_and_records_provenance(monkeypatch):
    captured = {}

    async def fake_chain(prompt_values):
        captured.update(prompt_values)
        return {"schema_equivalence": 80, "value_accuracy": 70,
                "completeness": 60, "notes": "some notes"}

    monkeypatch.setattr(adj, "_invoke_chain", fake_chain)
    schema = _schema()
    ground = {"students": [{"id": 1, "name": "Ada"}]}
    generated = {"students": [{"id": 1, "name": "Ada"}]}

    result = asyncio.run(adj.adjudicate(schema, schema, ground, generated))

    assert result["status"] == "ok"
    assert result["scores"] == {
        "schema_equivalence": 80, "value_accuracy": 70, "completeness": 60,
    }
    assert result["notes"] == "some notes"
    assert result["rubric_version"] == "adjudication_rubric_v1"
    assert isinstance(result["rubric_hash"], str) and result["rubric_hash"]
    assert result["metadata"]["provider"]
    assert adj.ADJUDICATION_RUBRIC.keys() == {
        "schema_equivalence", "value_accuracy", "completeness",
    }
    # the gold/generated schema dump must have reached the prompt values
    assert "students" in captured["gold_schema"]
    assert "students" in captured["generated_schema"]
    assert "students" in captured["ground_rows"]
    assert "students" in captured["generated_rows"]


def test_adjudicate_returns_error_status_on_failure(monkeypatch):
    async def fake_chain(prompt_values):
        raise RuntimeError("boom")

    monkeypatch.setattr(adj, "_invoke_chain", fake_chain)
    schema = _schema()
    result = asyncio.run(adj.adjudicate(schema, schema, {}, {}))
    assert result["status"] == "error"
    assert "RuntimeError" in result["error"]
    assert result["scores"] is None


def test_adjudicate_int_casts_string_scores(monkeypatch):
    async def fake_chain(prompt_values):
        return {"schema_equivalence": "85", "value_accuracy": 90,
                "completeness": 75, "notes": None}

    monkeypatch.setattr(adj, "_invoke_chain", fake_chain)
    schema = _schema()
    result = asyncio.run(adj.adjudicate(schema, schema, {}, {}))
    assert result["scores"]["schema_equivalence"] == 85
    assert result["scores"]["value_accuracy"] == 90


def test_adjudicate_returns_error_status_on_none_result(monkeypatch):
    async def fake_chain(prompt_values):
        return None

    monkeypatch.setattr(adj, "_invoke_chain", fake_chain)
    schema = _schema()
    result = asyncio.run(adj.adjudicate(schema, schema, {}, {}))
    assert result["status"] == "error"
    assert result["scores"] is None
    assert result["error"]