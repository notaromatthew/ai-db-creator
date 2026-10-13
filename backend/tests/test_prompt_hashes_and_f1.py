import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prompt_hashes = load_script("prompt_hashes")
f1_by_source = load_script("f1_by_source")


# --- hash dei prompt (7.2#1) ---------------------------------------------------------

def test_prompt_hashes_match_the_recorded_file():
    problems = prompt_hashes.diff(prompt_hashes.collect_prompts(), prompt_hashes.load_recorded())
    assert not problems, (
        "Un prompt e' cambiato senza aggiornare docs/prompt-hashes.json: " + "; ".join(problems)
        + ". Se la modifica e' voluta esegui `python scripts/prompt_hashes.py --write` "
          "e registrala nel changelog (docs/15-ai-agent-changelog.md)."
    )


def test_all_known_prompt_constants_are_tracked():
    keys = set(prompt_hashes.collect_prompts())
    for expected in ("backend/app/core/llm.py::SCHEMA_PROMPT", "backend/app/core/llm.py::QUERY_PROMPT",
                     "backend/app/core/llm.py::POPULATE_SQL_PROMPT",
                     "backend/app/services/chat_service.py::SYSTEM_PROMPT",
                     "backend/app/services/chat_service.py::EXTRACTION_PROMPT",
                     "backend/app/services/pdf_ocr.py::OCR_PROMPT",
                     "backend/app/services/schema_service.py::SCHEMA_REPAIR_PROMPT"):
        assert expected in keys


def make_repo(tmp_path, text):
    source = tmp_path / "backend" / "app" / "core"
    source.mkdir(parents=True)
    (source / "llm.py").write_text(text, encoding="utf-8")
    return tmp_path


def test_hash_changes_with_the_prompt_text_but_not_with_formatting(tmp_path):
    base = prompt_hashes.collect_prompts(make_repo(tmp_path / "a", 'SCHEMA_PROMPT = "Genera uno schema"\n'))
    reformatted = prompt_hashes.collect_prompts(make_repo(tmp_path / "b", '# commento\nSCHEMA_PROMPT   =   (\n  "Genera uno schema"\n)\n'))
    edited = prompt_hashes.collect_prompts(make_repo(tmp_path / "c", 'SCHEMA_PROMPT = "Genera uno schema 3NF"\n'))
    key = "backend/app/core/llm.py::SCHEMA_PROMPT"
    assert base[key] == reformatted[key]
    assert base[key] != edited[key]
    assert prompt_hashes.diff(edited, base) == [f"prompt modificato: {key}"]


def test_inline_templates_in_functions_are_tracked(tmp_path):
    code = ("from langchain_core.prompts import ChatPromptTemplate\n"
            "def run():\n    prompt = ChatPromptTemplate.from_messages([('system', 'ciao')])\n")
    found = prompt_hashes.collect_prompts(make_repo(tmp_path, code))
    assert "backend/app/core/llm.py::run#1" in found


def test_diff_reports_new_and_removed_prompts():
    assert prompt_hashes.diff({"a": "1", "b": "2"}, {"a": "1", "c": "3"}) == [
        "prompt nuovo non registrato: b", "prompt registrato ma non piu' presente: c"]


def test_write_then_check_roundtrip(tmp_path):
    target = tmp_path / "hashes.json"
    current = {"x::P": "abc"}
    prompt_hashes.write(current, target)
    assert json.loads(target.read_text())["prompts"] == current
    assert prompt_hashes.diff(current, prompt_hashes.load_recorded(target)) == []


# --- F1 per tipo di sorgente (7.3#2) -------------------------------------------------

SAMPLE = [
    {"source": "fatture.pdf", "tp": 8, "fp": 2, "fn": 2},
    {"source": "scan.PDF", "tp": 2, "fp": 0, "fn": 3},
    {"source": "ordini.xlsx", "tp": 10, "fp": 0, "fn": 0},
    {"source": "vecchio.xls", "tp": 5, "fp": 5, "fn": 0},
    {"source_type": "csv", "expected": [["persone", 1, "Ada"], ["persone", 2, "Linus"]],
     "predicted": [["persone", 1, "Ada"], ["persone", 3, "Grace"]]},
    {"source": "note.txt", "expected": ["a", "b", "c"], "predicted": ["a", "b", "c"]},
]


def test_f1_per_source_type_from_counts_and_sets():
    report = f1_by_source.f1_by_source(SAMPLE)
    by_type = report["by_source_type"]
    assert list(by_type) == ["pdf", "xlsx", "csv", "txt"]
    pdf = by_type["pdf"]
    assert (pdf["tp"], pdf["fp"], pdf["fn"], pdf["records"]) == (10, 2, 5, 2)
    assert pdf["precision"] == pytest.approx(10 / 12, abs=1e-4)
    assert pdf["recall"] == pytest.approx(10 / 15, abs=1e-4)
    assert pdf["f1"] == pytest.approx(2 * (10 / 12) * (10 / 15) / ((10 / 12) + (10 / 15)), abs=1e-4)
    xlsx = by_type["xlsx"]  # .xls conta come xlsx
    assert (xlsx["tp"], xlsx["fp"], xlsx["records"]) == (15, 5, 2)
    csv = by_type["csv"]
    assert (csv["tp"], csv["fp"], csv["fn"]) == (1, 1, 1) and csv["f1"] == 0.5
    assert by_type["txt"]["f1"] == 1.0
    assert report["macro_f1"] == pytest.approx(sum(v["f1"] for v in by_type.values()) / 4, abs=1e-4)


def test_empty_counts_give_zero_not_division_error():
    report = f1_by_source.f1_by_source([{"source": "vuoto.csv", "tp": 0, "fp": 0, "fn": 0}])
    assert report["by_source_type"]["csv"]["f1"] == 0.0


def test_unknown_extension_is_kept_and_invalid_record_rejected():
    report = f1_by_source.f1_by_source([{"source": "dati.json", "tp": 1, "fp": 0, "fn": 0}])
    assert "json" in report["by_source_type"]
    with pytest.raises(ValueError):
        f1_by_source.f1_by_source([{"source": "a.csv"}])


def test_cli_reads_a_results_file_and_writes_the_report(tmp_path, capsys):
    results = tmp_path / "risultati.json"
    results.write_text(json.dumps({"results": SAMPLE}), encoding="utf-8")
    output = tmp_path / "f1.json"
    assert f1_by_source.main([str(results), "--output", str(output)]) == 0
    assert json.loads(output.read_text())["by_source_type"]["txt"]["f1"] == 1.0
    assert "macro_f1" in capsys.readouterr().out
