import importlib.util
import sys
from pathlib import Path

from run_benchmark import BenchmarkRunner


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "data" / "datasets" / "format_equivalence"


def test_each_format_has_exactly_one_source_file():
    for source_format in ("csv", "xlsx", "txt", "pdf"):
        files = BenchmarkRunner._source_files("format_equivalence", source_format)
        assert len(files) == 1
        assert files[0].suffix.lower() == f".{source_format}"


def test_fixture_representations_are_semantically_equivalent():
    sys.path.insert(0, str(FIXTURE))
    try:
        spec = importlib.util.spec_from_file_location(
            "format_equivalence_validator", FIXTURE / "validate_fixture.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        result = module.validate()
    finally:
        sys.path.remove(str(FIXTURE))

    assert result == {
        "status": "valid",
        "record_count": 45,
        "field_count": 7,
        "formats": ["csv", "xlsx", "txt", "pdf"],
    }
