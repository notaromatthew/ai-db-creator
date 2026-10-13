import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models.database import Base

BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS_HEAD = "d4final00004"


def alembic_config(engine):
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["engine"] = engine
    return cfg


@pytest.fixture()
def engine(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migrazioni.db'}")
    yield engine
    engine.dispose()


def test_there_is_a_single_head_and_a_linear_chain(engine):
    script = ScriptDirectory.from_config(alembic_config(engine))
    assert len(script.get_heads()) == 1
    revisions = list(script.walk_revisions())
    assert all(len(rev.nextrev) <= 1 for rev in revisions)
    assert sum(1 for rev in revisions if rev.down_revision is None) == 1


def test_all_migrations_run_in_chain_on_an_empty_sqlite_up_to_head(engine):
    cfg = alembic_config(engine)
    command.upgrade(cfg, "head")
    head = ScriptDirectory.from_config(cfg).get_current_head()
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == head
    inspector = sa.inspect(engine)
    for table in ("projects", "users", "project_members", "chat_messages", "jobs", "schema_versions", "query_history"):
        assert table in inspector.get_table_names()
    assert {"schema_version", "target_dialect", "schema_finalized_at"} <= {c["name"] for c in inspector.get_columns("projects")}
    assert "needs_ocr" in {c["name"] for c in inspector.get_columns("documents")}


def test_migrated_schema_matches_the_models(engine):
    command.upgrade(alembic_config(engine), "head")
    inspector = sa.inspect(engine)
    for table in Base.metadata.sorted_tables:
        assert table.name in inspector.get_table_names(), table.name
        assert {c.name for c in table.columns} <= {c["name"] for c in inspector.get_columns(table.name)}, table.name


def test_downgrade_and_upgrade_again(engine):
    cfg = alembic_config(engine)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, PREVIOUS_HEAD)
    inspector = sa.inspect(engine)
    assert "jobs" not in inspector.get_table_names()
    assert "needs_ocr" not in {c["name"] for c in inspector.get_columns("documents")}
    command.upgrade(cfg, "head")
    assert "jobs" in sa.inspect(engine).get_table_names()


def test_migration_is_idempotent_when_create_all_already_made_the_new_tables(engine):
    cfg = alembic_config(engine)
    command.upgrade(cfg, PREVIOUS_HEAD)
    # come al riavvio di un database gia' versionato: create_all aggiunge le tabelle nuove prima dell'upgrade
    Base.metadata.create_all(engine)
    command.upgrade(cfg, "head")
    assert "schema_versions" in sa.inspect(engine).get_table_names()


def test_existing_schemas_get_version_one(engine):
    cfg = alembic_config(engine)
    command.upgrade(cfg, PREVIOUS_HEAD)
    schema = {"tables": [{"name": "t", "columns": []}], "relationships": []}
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO users (id, blocked) VALUES ('u1', 0)"))
        conn.execute(sa.text("INSERT INTO projects (id, owner_id, name, schema_json) VALUES ('p1', 'u1', 'Con schema', :s)"),
                     {"s": json.dumps(schema)})
        conn.execute(sa.text("INSERT INTO projects (id, owner_id, name) VALUES ('p2', 'u1', 'Senza schema')"))
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        rows = conn.execute(sa.text("SELECT project_id, version, origin, author FROM schema_versions")).fetchall()
        versions = dict(conn.execute(sa.text("SELECT id, schema_version FROM projects")).fetchall())
    assert rows == [("p1", 1, "generazione", "u1")]
    assert versions == {"p1": 1, "p2": 0}


def test_run_migrations_on_a_fresh_database_stamps_head(engine):
    from app.models.database import run_migrations
    Base.metadata.create_all(engine)
    run_migrations(engine)
    with engine.connect() as conn:
        version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    assert version == ScriptDirectory.from_config(alembic_config(engine)).get_current_head()


def test_g7_adds_unique_active_job_and_participant_indexes_and_is_idempotent(engine):
    cfg = alembic_config(engine)
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["g7hardening00007"]
    assert script.get_revision("g7hardening00007").down_revision == "f6research00006"
    command.upgrade(cfg, "f6research00006")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO users (id, blocked) VALUES ('u1', 0)"))
        conn.execute(sa.text("INSERT INTO projects (id, owner_id, name) VALUES ('p1', 'u1', 'P')"))
        for jid in ("a", "b"):  # duplicato attivo pre-esistente
            conn.execute(sa.text("INSERT INTO jobs (id, project_id, user_id, kind, status, progress) "
                                 "VALUES (:i, 'p1', 'u1', 'schema', 'queued', 0)"), {"i": jid})
    command.upgrade(cfg, "head")
    inspector = sa.inspect(engine)
    assert {"uq_jobs_active_project"} <= {i["name"] for i in inspector.get_indexes("jobs")}
    assert "account_hash" in {c["name"] for c in inspector.get_columns("study_participants")}
    with engine.begin() as conn:
        statuses = [r[0] for r in conn.execute(sa.text("SELECT status FROM jobs ORDER BY id"))]
    assert sorted(statuses) == ["failed", "queued"]
    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO jobs (id, project_id, user_id, kind, status, progress) "
                                 "VALUES ('c', 'p1', 'u1', 'dati', 'running', 0)"))
    command.downgrade(cfg, "f6research00006")
    command.upgrade(cfg, "head")
    Base.metadata.create_all(engine)
    command.downgrade(cfg, "f6research00006")
    Base.metadata.create_all(engine)
    command.upgrade(cfg, "head")  # idempotente con colonna/indici gia' presenti
