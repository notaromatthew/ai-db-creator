import csv
import io

from app.api.routes import _schema_edit_counts
from app.config import settings
from app.models import database
from app.models.schema_models import ColumnDef
from app.services import research_study
from app.services.interaction_logger import interaction_logger
from schema_factories import valid_schema


def test_schema_diff_emits_granular_rq4_counts():
    previous = valid_schema()
    current = previous.model_copy(deep=True)
    current.tables[1].columns.append(ColumnDef(name="isbn", data_type="TEXT", is_unique=True))
    current.tables[0].columns[1].data_type = "VARCHAR"
    current.tables[0].columns[1].is_not_null = True
    current.relationships = []
    assert _schema_edit_counts(previous, current) == {
        "column_added": 1,
        "type_changed": 1,
        "not_null_toggled": 1,
        "relationship_removed": 1,
    }


def test_combined_export_and_withdrawal_cover_app_telemetry(tmp_path):
    original_url = settings.database_url
    settings.database_url = f"sqlite:///{tmp_path / 'study.db'}"
    engine = database.init_db(settings.database_url)
    try:
        interaction_logger.persist_path = tmp_path / "interactions.json"
        interaction_logger.events = []
        participant = research_study.enroll(True, research_study.CONSENT_VERSION, {
            "role": "studente", "db_experience": 2, "ai_experience": 3,
        }, research_study.account_hash("account-a"))
        pid = participant["participant_id"]
        research_study.add_event(pid, participant["code"], "task_start", {})
        interaction_logger.log_event("schema_updated", "project-a", {
            "participant_id": pid, "edit_counts": {"column_added": 2},
        })
        rows = list(csv.DictReader(io.StringIO(research_study.export_csv("interactions"))))
        assert [row["type"] for row in rows].count("task_start") == 1
        assert [row["type"] for row in rows].count("column_added") == 2
        assert research_study.active_context(pid, participant["arm"], research_study.account_hash("account-a"))
        research_study.withdraw(pid, participant["code"])
        assert interaction_logger.get_events() == []
    finally:
        engine.dispose()
        database._engine = None
        settings.database_url = original_url
