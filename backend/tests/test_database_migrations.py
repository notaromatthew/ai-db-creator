from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text

from app.models.database import Base, verify_schema_compatibility
from migrate_database import _config, migrate


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def assert_current(url: str) -> None:
    engine = create_engine(url)
    verify_schema_compatibility(engine)
    inspector = inspect(engine)
    assert set(Base.metadata.tables) <= set(inspector.get_table_names())
    assert inspector.get_table_names().count("alembic_version") == 1


def test_empty_database_upgrades_to_head(tmp_path):
    url = sqlite_url(tmp_path / "empty.db")
    assert migrate(url) == "initialized"
    assert_current(url)


def test_historical_alembic_revision_upgrades_to_head(tmp_path):
    url = sqlite_url(tmp_path / "historical.db")
    command.upgrade(_config(url), "c25c5721cbb9")
    assert migrate(url) == "upgraded"
    assert_current(url)


def test_current_pre_alembic_database_is_verified_then_stamped(tmp_path):
    url = sqlite_url(tmp_path / "current.db")
    Base.metadata.create_all(create_engine(url))
    assert migrate(url) == "stamped_current"
    assert_current(url)


def test_unrecognized_legacy_database_fails_closed(tmp_path):
    url = sqlite_url(tmp_path / "unknown.db")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL)"))
    with pytest.raises(RuntimeError, match="automatic migration refused"):
        migrate(url)


def test_current_named_but_wrong_constraints_fails_closed(tmp_path):
    url = sqlite_url(tmp_path / "wrong-shape.db")
    Base.metadata.create_all(create_engine(url))
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE documents"))
        connection.execute(text(
            "CREATE TABLE documents (id VARCHAR, project_id VARCHAR NOT NULL, filename VARCHAR(255) NOT NULL, "
            "file_type VARCHAR(10) NOT NULL, file_path VARCHAR(512) NOT NULL, content_summary TEXT, created_at DATETIME)"
        ))
    with pytest.raises(RuntimeError, match="automatic migration refused"):
        migrate(url)


def test_historical_named_but_wrong_or_extra_layout_fails_closed(tmp_path):
    url = sqlite_url(tmp_path / "wrong-historical.db")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id VARCHAR, name VARCHAR(255) NOT NULL, prompt TEXT, schema_json JSON, db_path VARCHAR(512), created_at DATETIME, updated_at DATETIME)"))
        connection.execute(text("CREATE TABLE documents (id VARCHAR PRIMARY KEY, project_id VARCHAR NOT NULL, filename VARCHAR(255) NOT NULL, file_type VARCHAR(10) NOT NULL, file_path VARCHAR(512) NOT NULL, content_summary TEXT, created_at DATETIME)"))
        connection.execute(text("CREATE TABLE unexpected (id INTEGER PRIMARY KEY)"))
    with pytest.raises(RuntimeError, match="automatic migration refused"):
        migrate(url)
