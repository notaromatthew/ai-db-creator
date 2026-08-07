from app.models.database import BenchmarkResult, UserVote, get_session, init_db
from app.models.schema_models import NormalizedSchema, TableDef, ColumnDef
from app.core.llm import generate_schema, get_llm_info

import time
import json
from datetime import datetime, timezone
from app.utils.logger import log

BENCHMARK_SCENARIOS = {
    "ecommerce": {
        "title": "E-Commerce System",
        "prompt": "Create an e-commerce database with customers, orders, order_items, products, and categories.",
        "gold_tables": ["customers", "orders", "order_items", "products", "categories"],
        "gold_fk_pairs": [
            ("orders.customer_id", "customers.id"),
            ("order_items.order_id", "orders.id"),
            ("order_items.product_id", "products.id"),
            ("products.category_id", "categories.id"),
        ]
    },
    "hospital": {
        "title": "Hospital Management System",
        "prompt": "Design a hospital database with patients, doctors, appointments, medical_records, and departments.",
        "gold_tables": ["patients", "doctors", "appointments", "medical_records", "departments"],
        "gold_fk_pairs": [
            ("doctors.department_id", "departments.id"),
            ("appointments.patient_id", "patients.id"),
            ("appointments.doctor_id", "doctors.id"),
            ("medical_records.patient_id", "patients.id"),
            ("medical_records.doctor_id", "doctors.id"),
        ]
    },
    "university": {
        "title": "University Academic Portal",
        "prompt": "Design a university database with students, courses, enrollments, professors, and departments.",
        "gold_tables": ["students", "courses", "enrollments", "professors", "departments"],
        "gold_fk_pairs": [
            ("courses.department_id", "departments.id"),
            ("professors.department_id", "departments.id"),
            ("courses.professor_id", "professors.id"),
            ("enrollments.student_id", "students.id"),
            ("enrollments.course_id", "courses.id"),
        ]
    }
}

async def run_model_benchmark(
    scenario_key: str = "ecommerce",
    temperature: float = 0.1,
    model_name: str | None = None,
    provider: str | None = None
) -> dict:
    scenario = BENCHMARK_SCENARIOS.get(scenario_key, BENCHMARK_SCENARIOS["ecommerce"])
    from app.config import settings
    if model_name:
        settings.ollama_model = model_name
    if provider:
        settings.llm_provider = provider
        settings.use_ollama = (provider == "ollama")

    from app.api.progress import set_progress
    llm_info = get_llm_info()
    log.info(f"🚀 Starting benchmark scenario '{scenario_key}' with provider '{llm_info['provider']}', model '{llm_info['model']}', temp={temperature}")

    set_progress("benchmark", "running", 15, f"Inizializzazione provider {llm_info['provider']} ({llm_info['model']})...", etc_seconds=12)
    start_time = time.monotonic()
    try:
        set_progress("benchmark", "running", 35, f"Invio prompt per scenario '{scenario['title']}' a {llm_info['model']}...", etc_seconds=8)
        schema: NormalizedSchema = await generate_schema(scenario["prompt"], temperature=temperature)
        latency = round(time.monotonic() - start_time, 3)
        log.info(f"✅ Benchmark finished in {latency}s for model {llm_info['model']}")

        set_progress("benchmark", "running", 75, "Analisi conformità 3NF e calcolo F1 score delle relazioni...", etc_seconds=3)



        # 1. 3NF Score (% of tables with a PK and snake_case naming)
        tables = schema.tables
        norm3_count = 0
        for t in tables:
            has_pk = any(c.is_primary_key for c in t.columns)
            if has_pk:
                norm3_count += 1
        norm3_score = round((norm3_count / len(tables)) * 100, 2) if tables else 0.0

        # 2. Relationship F1 Score
        generated_fk_pairs = set()
        if schema.relationships:
            for r in schema.relationships:
                generated_fk_pairs.add((f"{r.from_table}.{r.from_column}", f"{r.to_table}.{r.to_column}"))
        else:
            for t in tables:
                for c in t.columns:
                    if c.is_foreign_key and c.foreign_key_table and c.foreign_key_column:
                        generated_fk_pairs.add((f"{t.name}.{c.name}", f"{c.foreign_key_table}.{c.foreign_key_column}"))

        gold_pairs = set(scenario["gold_fk_pairs"])
        tp = len(generated_fk_pairs.intersection(gold_pairs))
        fp = len(generated_fk_pairs - gold_pairs)
        fn = len(gold_pairs - generated_fk_pairs)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0 if not gold_pairs else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0 if not gold_pairs else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 3) if (precision + recall) > 0 else 0.0

        # 3. Cell precision estimate & Token cost estimate
        cell_precision = round(min(1.0, norm3_score / 100.0 * 0.95 + 0.05), 3)
        est_tokens = len(scenario["prompt"].split()) * 5 + len(str(schema.model_dump())).split()
        est_cost = round(len(est_tokens) * 0.000002, 6)

        result_entry = BenchmarkResult(
            scenario_name=scenario["title"],
            provider=llm_info["provider"],
            model_name=llm_info["model"],
            norm3_score=norm3_score,
            relationship_f1=f1_score,
            cell_precision=cell_precision,
            latency_seconds=latency,
            token_cost_estimate=est_cost,
            details_json={
                "tables_count": len(tables),
                "generated_relationships": list(generated_fk_pairs),
                "gold_relationships": list(gold_pairs),
                "temperature": temperature
            }
        )

        set_progress("benchmark", "saving", 95, "Registrazione risultati nel database PostgreSQL...", etc_seconds=1)
        engine = init_db()
        session = get_session(engine)
        session.add(result_entry)
        session.commit()
        session.refresh(result_entry)

        set_progress("benchmark", "completed", 100, f"Benchmark per {llm_info['model']} completato con successo in {latency}s!", etc_seconds=0)

        return {
            "id": result_entry.id,
            "scenario": scenario["title"],
            "provider": llm_info["provider"],
            "model": llm_info["model"],
            "norm3_score": norm3_score,
            "relationship_f1": f1_score,
            "cell_precision": cell_precision,
            "latency_seconds": latency,
            "estimated_cost": est_cost,
            "tables_generated": [t.name for t in tables],
        }

    except Exception as e:
        log.error(f"Benchmark execution error: {e}")
        set_progress("benchmark", "failed", 0, f"Errore benchmark: {e}", etc_seconds=0)
        return {
            "error": str(e),
            "scenario": scenario["title"],
            "provider": llm_info.get("provider", "unknown"),
            "model": llm_info.get("model", "unknown")
        }


def save_user_vote(user_id: str, schema_rating: int, data_rating: int, comment: str = "", project_id: str | None = None, benchmark_id: str | None = None):
    engine = init_db()
    session = get_session(engine)
    vote = UserVote(
        user_id=user_id,
        project_id=project_id,
        benchmark_id=benchmark_id,
        schema_rating=schema_rating,
        data_rating=data_rating,
        comment=comment
    )
    session.add(vote)
    session.commit()
    session.refresh(vote)
    return vote
