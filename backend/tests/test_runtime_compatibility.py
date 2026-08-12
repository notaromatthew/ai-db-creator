from pathlib import Path


def test_postgres_driver_pin_supports_python_313_wheels():
    requirements = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert "psycopg2-binary==2.9.10" in requirements.splitlines()
    assert "psycopg2-binary==2.9.9" not in requirements.splitlines()
