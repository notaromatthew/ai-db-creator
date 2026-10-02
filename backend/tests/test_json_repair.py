import pytest
from app.utils.json_repair import repair_and_load_json


def test_repair_trailing_commas():
    raw = '{"tables": [{"name": "clienti", "columns": [{"name": "id", "data_type": "INTEGER",},],},],}'
    data = repair_and_load_json(raw)
    assert "tables" in data
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "clienti"


def test_repair_markdown_code_block():
    raw = """Ecco lo schema:
```json
{
  "schema": {
    "tables": [
      {
        "name": "prodotti",
        "columns": [
          {"name": "id", "data_type": "INTEGER"}
        ]
      }
    ]
  }
}
```
Spero sia utile!"""
    data = repair_and_load_json(raw)
    assert "schema" in data or "tables" in data


def test_repair_truncated_json():
    raw = '{"tables": [{"name": "ordini", "columns": [{"name": "id", "data_type": "INTEGER"'
    data = repair_and_load_json(raw)
    assert "tables" in data
    assert data["tables"][0]["name"] == "ordini"
