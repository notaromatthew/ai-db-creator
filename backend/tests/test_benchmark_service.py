import asyncio

from app.models.schema_models import ColumnDef, NormalizedSchema, TableDef
from app.config import settings
from app.services import benchmark_service


class FakeSession:
    def __init__(self):
        self.added = None

    def add(self, value):
        self.added = value

    def commit(self):
        pass

    def refresh(self, value):
        value.id = "benchmark-1"


def test_run_model_benchmark_returns_and_persists_metrics(monkeypatch):
    schema = NormalizedSchema(
        tables=[
            TableDef(
                name="customers",
                columns=[ColumnDef(name="id", data_type="INTEGER", is_primary_key=True)],
            )
        ],
        relationships=[],
    )

    async def fake_generate_schema(*_args, **_kwargs):
        return schema

    session = FakeSession()
    monkeypatch.setattr(benchmark_service, "generate_schema", fake_generate_schema)
    monkeypatch.setattr(
        benchmark_service,
        "get_llm_info",
        lambda **_kwargs: {"provider": "test", "model": "deterministic-model"},
    )
    monkeypatch.setattr(benchmark_service, "init_db", lambda: object())
    monkeypatch.setattr(benchmark_service, "get_session", lambda _engine: session)

    result = asyncio.run(benchmark_service.run_model_benchmark("ecommerce"))

    assert "error" not in result
    assert result["id"] == "benchmark-1"
    assert result["norm3_score"] == 100.0
    assert "cell_precision" not in result
    assert result["rq2_cell_precision"] is None
    assert result["schema_quality_heuristic_estimate"] == 1.0
    assert isinstance(result["estimated_cost"], float)
    assert session.added is not None
    assert session.added.token_cost_estimate == result["estimated_cost"]
    assert session.added.details_json["data_metric"]["is_rq2_measure"] is False


def test_concurrent_benchmarks_keep_provider_model_and_global_settings_isolated(monkeypatch):
    schema = NormalizedSchema(
        tables=[
            TableDef(
                name="customers",
                columns=[ColumnDef(name="id", data_type="INTEGER", is_primary_key=True)],
            )
        ],
        relationships=[],
    )
    calls = []

    async def fake_generate_schema(*_args, **kwargs):
        calls.append((kwargs["provider"], kwargs["model"]))
        await asyncio.sleep(0)
        return schema

    sessions = []
    progress_events = []

    def session_factory(_engine):
        session = FakeSession()
        sessions.append(session)
        return session

    snapshot = (settings.llm_provider, settings.use_ollama, settings.ollama_model, settings.google_model)
    monkeypatch.setattr(benchmark_service, "generate_schema", fake_generate_schema)
    monkeypatch.setattr(benchmark_service, "init_db", lambda: object())
    monkeypatch.setattr(benchmark_service, "get_session", session_factory)
    from app.api import progress as progress_api
    monkeypatch.setattr(
        progress_api,
        "set_progress",
        lambda key, status, progress, message="", etc_seconds=None: progress_events.append(
            (key, status, progress, message)
        ),
    )

    async def run_both():
        return await asyncio.gather(
            benchmark_service.run_model_benchmark(
                "ecommerce", provider="google", model_name="gemini-test",
                progress_key="benchmark:user-google",
            ),
            benchmark_service.run_model_benchmark(
                "hospital", provider="ollama", model_name="ollama-test",
                progress_key="benchmark:user-ollama",
            ),
        )

    google_result, ollama_result = asyncio.run(run_both())

    assert set(calls) == {("google", "gemini-test"), ("ollama", "ollama-test")}
    assert google_result["provider"] == "Google Gemini"
    assert google_result["model"] == "gemini-test"
    assert ollama_result["provider"].startswith("Ollama")
    assert ollama_result["model"] == "ollama-test"
    assert (settings.llm_provider, settings.use_ollama, settings.ollama_model, settings.google_model) == snapshot
    assert len(sessions) == 2
    assert {event[0] for event in progress_events} == {
        "benchmark:user-google", "benchmark:user-ollama"
    }
    assert all(
        "ollama-test" not in event[3]
        for event in progress_events if event[0] == "benchmark:user-google"
    )
    assert all(
        "gemini-test" not in event[3]
        for event in progress_events if event[0] == "benchmark:user-ollama"
    )
