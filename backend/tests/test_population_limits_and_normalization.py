import asyncio

import pytest
from sqlalchemy import create_engine, text

from app.core.runtime import DEFAULTS
from app.models.schema_models import ColumnDef, NormalizedSchema, TableDef
from app.services import population_service
from app.services.population_service import (
    DEFAULT_MAX_CHARS_PER_REQUEST, PopulationService, max_chars_per_request, normalize_value, split_text,
)

from test_population_pipeline import add_csv, add_text


# --- suddivisione dei documenti lunghi (2.2#1) -------------------------------------

def test_default_cap_is_60000_without_runtime_setting():
    assert DEFAULT_MAX_CHARS_PER_REQUEST == 60000
    assert "max_chars_per_request" not in DEFAULTS
    assert max_chars_per_request() == 60000


def test_cap_reads_runtime_setting_only_when_it_exists(monkeypatch):
    import app.core.runtime as runtime
    monkeypatch.setattr(runtime, "get_setting", lambda key: 1234 if key == "max_chars_per_request" else 0)
    assert max_chars_per_request() == 1234
    monkeypatch.setattr(runtime, "get_setting", lambda key: "non un numero")
    assert max_chars_per_request() == 60000
    monkeypatch.setattr(runtime, "get_setting", lambda key: 10)  # valore irragionevole
    assert max_chars_per_request() == 60000


def test_short_text_is_not_split():
    assert split_text("abc", 100) == ["abc"]


def test_split_text_respects_cap_overlaps_and_covers_everything():
    lines = [f"riga {i:04d} " + "x" * 30 for i in range(200)]
    body = "\n".join(lines)
    chunks = split_text(body, 1000, overlap=200)
    assert len(chunks) > 5
    assert all(len(chunk) <= 1000 for chunk in chunks)
    for first, second in zip(chunks, chunks[1:]):
        assert first[-100:] and second[:50] in body
        tail_lines = set(first.splitlines()[-4:])
        assert tail_lines & set(second.splitlines()[:8])  # sovrapposizione
    assert "riga 0000" in chunks[0] and "riga 0199" in chunks[-1]
    covered = {line for chunk in chunks for line in chunk.splitlines()}
    assert covered >= set(lines)


def test_split_text_without_newlines_still_progresses():
    chunks = split_text("a" * 5000, 1000, overlap=5000)
    assert all(len(chunk) <= 1000 for chunk in chunks)
    assert len(chunks) >= 5


def persons():
    return NormalizedSchema(tables=[TableDef(name="persone", columns=[
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
        ColumnDef(name="nome", data_type="TEXT"),
    ])], relationships=[])


def test_long_document_is_split_into_requests_and_results_are_merged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(population_service, "DEFAULT_MAX_CHARS_PER_REQUEST", 2000)
    service = PopulationService()
    body = "\n".join(f"Persona {i}: nome{i}" for i in range(400))
    document_id = add_text(service, tmp_path, "p1", content=body)
    seen = []

    async def sql(_schema, content, temperature=None):
        seen.append(content)
        numbers = sorted({int(token.split(":")[0]) for token in content.replace("Persona ", "#").split("#")[1:]
                          if token.split(":")[0].isdigit()})
        # il blocco di sovrapposizione fa ripetere alcune righe: lo stesso INSERT arriva in due blocchi
        return ";".join(f"INSERT INTO persone (id, nome) VALUES ({n}, 'nome{n}')" for n in numbers)

    monkeypatch.setattr(population_service, "generate_sql_for_population", sql)
    monkeypatch.setattr(population_service, "MAX_CHUNKS_PER_RUN", 50)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), persons(), [document_id]))
    assert len(seen) > 1 and all(len(chunk) <= 2000 for chunk in seen)
    table = result["persone"]
    assert table["inserted"] == 400
    assert table["failed"] == 0
    assert any(w["category"] == "llm_input_split" and w["chunks"] == len(seen) for w in table["warnings"])
    with create_engine(f"sqlite:///{tmp_path / 'database.sqlite'}").connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM persone")).scalar() == 400


def test_more_chunks_than_the_limit_are_truncated_with_a_warning(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(population_service, "DEFAULT_MAX_CHARS_PER_REQUEST", 1000)
    monkeypatch.setattr(population_service, "MAX_CHUNKS_PER_RUN", 3)
    service = PopulationService()
    ids = [add_text(service, tmp_path, "p1", filename=f"s{i}.txt", content=("riga lunga " * 80 + "\n") * 2) for i in range(4)]
    calls = []

    async def sql(_schema, content, temperature=None):
        calls.append(content)
        return ""

    async def no_rows(table_def, content):
        return []

    monkeypatch.setattr(population_service, "generate_sql_for_population", sql)
    monkeypatch.setattr(population_service, "generate_data_for_table", no_rows)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), persons(), ids))
    assert len(calls) == 3
    assert any(w["category"] == "llm_input_truncated" for w in result["persone"]["warnings"])


# --- normalizzazione di tipi e date (7.3#0) ----------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("2024-03-05", "2024-03-05"),
    ("05/03/2024", "2024-03-05"),
    ("5-3-2024", "2024-03-05"),
    ("05.03.2024", "2024-03-05"),
    ("2024/03/05", "2024-03-05"),
    ("5/3/24", "2024-03-05"),
    ("20240305", "2024-03-05"),
    ("5 marzo 2024", "2024-03-05"),
    ("12 gen 2020", "2020-01-12"),
    ("March 5, 2024", "2024-03-05"),
    ("2024-03-05 00:00:00", "2024-03-05"),
    ("data sconosciuta", "data sconosciuta"),
    ("31/02/2024", "31/02/2024"),
])
def test_dates_become_iso(raw, expected):
    assert normalize_value(raw, "DATE") == expected


@pytest.mark.parametrize("raw,expected", [
    ("2024-03-05 14:30:00", "2024-03-05 14:30:00"),
    ("05/03/2024 14:30", "2024-03-05 14:30:00"),
    ("2024-03-05T14:30:00Z", "2024-03-05 14:30:00"),
    ("05/03/2024", "2024-03-05"),
])
def test_datetimes_become_iso(raw, expected):
    assert normalize_value(raw, "DATETIME") == expected


@pytest.mark.parametrize("raw,data_type,expected", [
    ("1.234,56", "REAL", 1234.56),
    ("1,5", "REAL", 1.5),
    ("1,234.56", "REAL", 1234.56),
    ("12,50 €", "FLOAT", 12.5),
    ("3.14", "REAL", 3.14),
    ("1.234.567", "REAL", 1234567.0),
    ("-0,5", "REAL", -0.5),
    ("1e3", "REAL", 1000.0),
    ("1.234", "INTEGER", 1234),
    ("1,234", "INTEGER", 1234),
    ("42", "INTEGER", 42),
    ("42,0", "INTEGER", 42),
    ("3.0", "INTEGER", 3),
    ("abc", "INTEGER", "abc"),
    (7.0, "INTEGER", 7),
])
def test_numbers_with_decimal_comma(raw, data_type, expected):
    assert normalize_value(raw, data_type) == expected


@pytest.mark.parametrize("raw,expected", [
    ("si", 1), ("Sì", 1), ("Vero", 1), ("TRUE", 1), ("1", 1), ("yes", 1),
    ("no", 0), ("Falso", 0), ("false", 0), ("0", 0), (True, 1), (False, 0),
    ("forse", "forse"),
])
def test_booleans(raw, expected):
    assert normalize_value(raw, "BOOLEAN") == expected


@pytest.mark.parametrize("raw", ["", "   ", "nan", "NaN", "null", "None", "N/A", "NaT", None, float("nan")])
@pytest.mark.parametrize("data_type", ["TEXT", "INTEGER", "REAL", "DATE", "BOOLEAN", None])
def test_empty_strings_and_placeholders_become_null(raw, data_type):
    assert normalize_value(raw, data_type) is None


def test_text_is_only_trimmed():
    assert normalize_value("  Ada Lovelace  ", "TEXT") == "Ada Lovelace"
    assert normalize_value("007", "TEXT") == "007"
    assert normalize_value("1,5", "TEXT") == "1,5"
    assert normalize_value("05/03/2024", "TEXT") == "05/03/2024"


def test_python_date_objects_become_iso():
    from datetime import date, datetime
    assert normalize_value(date(2024, 3, 5), "DATE") == "2024-03-05"
    assert normalize_value(datetime(2024, 3, 5, 1, 2, 3), "DATETIME") == "2024-03-05 01:02:03"


def test_deterministic_import_applies_normalization_to_inserted_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    schema = NormalizedSchema(tables=[TableDef(name="ordini", columns=[
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
        ColumnDef(name="data", data_type="DATE"),
        ColumnDef(name="importo", data_type="REAL"),
        ColumnDef(name="pagato", data_type="BOOLEAN"),
        ColumnDef(name="nota", data_type="TEXT"),
    ])], relationships=[])
    path = tmp_path / "ordini.csv"
    path.write_text("id;data;importo;pagato;nota\n1;05/03/2024;\"1.234,50\";si;  ciao \n2;06/03/2024;7,5;no;nan\n",
                    encoding="utf-8")
    from app.models.database import Document, get_session
    service = PopulationService()
    session = get_session(service.engine)
    document = Document(project_id="p1", filename="ordini.csv", file_type="csv", file_path=str(path), content_summary="")
    session.add(document); session.commit(); document_id = document.id; session.close()

    async def no_sql(*args, **kwargs):
        return ""

    monkeypatch.setattr(population_service, "generate_sql_for_population", no_sql)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema, [document_id]))
    assert result["ordini"]["inserted"] == 2
    with create_engine(f"sqlite:///{tmp_path / 'database.sqlite'}").connect() as conn:
        rows = conn.execute(text("SELECT id, data, importo, pagato, nota FROM ordini ORDER BY id")).fetchall()
    assert rows[0] == (1, "2024-03-05", 1234.5, 1, "ciao")
    assert rows[1] == (2, "2024-03-06", 7.5, 0, None)
