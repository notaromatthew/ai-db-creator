import json
from datetime import datetime
from app.utils.logger import log
from app.models.database import get_session, init_db, Project
from app.models.schema_models import NormalizedSchema

class MetricsService:
    """Service for computing research metrics on generated schemas."""

    def __init__(self):
        self.engine = init_db()

    def check_3nf(self, schema: NormalizedSchema) -> dict:
        """Check if all tables are in 3NF."""
        results = {"tables": [], "all_3nf": True, "score": 0.0}
        for table in schema.tables:
            pk_cols = [c for c in table.columns if c.is_primary_key]
            non_key_attrs = [c for c in table.columns if not c.is_primary_key]
            has_transitive = False
            if pk_cols and len(non_key_attrs) > 1:
                unique_non_keys = [c for c in non_key_attrs if c.is_unique]
                if unique_non_keys:
                    non_uk_attrs = [c for c in non_key_attrs if not c.is_unique]
                    has_transitive = len(non_uk_attrs) > 0
            is_3nf = not has_transitive
            if not is_3nf:
                results["all_3nf"] = False
            results["tables"].append({
                "name": table.name,
                "is_3nf": is_3nf,
                "non_key_columns": len(non_key_attrs),
                "primary_key_columns": len(pk_cols),
            })
        results["score"] = sum(1 for t in results["tables"] if t["is_3nf"]) / max(len(results["tables"]), 1)
        return results

    def relationship_f1(self, schema: NormalizedSchema, expected_relationships: list = None) -> dict:
        """Compute F1 score for identified relationships."""
        predicted = set()
        for rel in schema.relationships:
            key = f"{rel.from_table}->{rel.to_table}"
            predicted.add(key)

        if expected_relationships:
            expected = set(expected_relationships)
            tp = len(predicted & expected)
            fp = len(predicted - expected)
            fn = len(expected - predicted)
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            return {"precision": precision, "recall": recall, "f1": f1}
        return {"predicted": list(predicted), "count": len(predicted)}

    def data_quality(self, project_id: str, db_path: str, schema: NormalizedSchema) -> dict:
        """Compute data quality metrics."""
        from sqlalchemy import create_engine, inspect, text
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        results = {"tables": {}, "total_duplicates": 0, "total_records": 0}

        valid_tables = {t.name for t in schema.tables}
        with engine.connect() as conn:
            for table in schema.tables:
                if table.name not in valid_tables:
                    continue
                cols = [c["name"] for c in inspector.get_columns(table.name)]
                pk_cols = [c["name"] for c in table.columns if c.is_primary_key]
                result = conn.execute(text(f"SELECT COUNT(*) FROM [{table.name}]"))
                count = result.scalar()
                results["tables"][table.name] = {"records": count, "columns": len(cols)}
                results["total_records"] += count

                if pk_cols:
                    pk_str = ", ".join(f"[{p}]" for p in pk_cols)
                    dup_sql = f"SELECT {pk_str}, COUNT(*) as cnt FROM [{table.name}] GROUP BY {pk_str} HAVING COUNT(*) > 1"
                    try:
                        dup_result = conn.execute(text(dup_sql))
                        dups = dup_result.fetchall()
                        results["tables"][table.name]["duplicates"] = len(dups)
                        results["total_duplicates"] += len(dups)
                    except Exception:
                        results["tables"][table.name]["duplicates"] = 0

        return results

    def save_metrics(self, project_id: str, metrics: dict):
        """Save metrics to project record."""
        session = get_session(self.engine)
        project = session.query(Project).filter(Project.id == project_id).first()
        if project:
            existing = project.schema_json or {}
            existing["_metrics"] = metrics
            existing["_metrics_timestamp"] = datetime.now().isoformat()
            project.schema_json = existing
            session.commit()
        session.close()
