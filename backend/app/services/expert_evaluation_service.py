"""Expert evaluation service for RQ1 schema assessments.

Loads condition-blind schemas (S01..S30) from backend/reports/rq1_expert_package,
handles online Likert ratings from experts, joins unblinded metadata from mapping.csv,
and aggregates statistical results for researchers/administrators.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from app.config import settings
from app.models.database import ExpertEvaluation, get_session
from app.utils.logger import log


class ExpertEvaluationService:
    def __init__(self, package_dir: Optional[str] = None):
        self.package_dir = Path(package_dir or settings.expert_package_dir)
        if not self.package_dir.is_absolute():
            self.package_dir = (Path(__file__).resolve().parent.parent.parent / self.package_dir).resolve()
        self._schemas_cache: Dict[str, Dict[str, Any]] = {}
        self._mapping_cache: Dict[str, Dict[str, str]] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load schemas and researcher mapping into memory."""
        # 1. Load mapping.csv
        mapping_path = self.package_dir / "mapping.csv"
        if mapping_path.exists():
            with mapping_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._mapping_cache[row["code"]] = {
                        "code": row["code"],
                        "dataset": row["dataset"],
                        "condition": row["condition"],
                        "run": row["run"],
                    }

        # 2. Load schemas/S*.md
        schemas_dir = self.package_dir / "schemas"
        if schemas_dir.exists():
            for schema_path in sorted(schemas_dir.glob("S*.md")):
                code = schema_path.stem
                parsed = self._parse_schema_file(code, schema_path)
                self._schemas_cache[code] = parsed

        log.info(f"ExpertEvaluationService: loaded {len(self._schemas_cache)} schemas and {len(self._mapping_cache)} mappings")

    def _parse_schema_file(self, code: str, path: Path) -> Dict[str, Any]:
        """Parse schema markdown into structured schema objects."""
        raw_markdown = path.read_text(encoding="utf-8")
        tables: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        current_table: Optional[Dict[str, Any]] = None
        desc_lines: List[str] = []
        in_header = True

        for line in raw_markdown.splitlines():
            if line.startswith("---"):
                in_header = False
                continue
            if in_header:
                continue

            if line.startswith("TABLE "):
                current_table = {"name": line.replace("TABLE ", "").strip(), "columns": []}
                tables.append(current_table)
            elif line.startswith("RELATIONSHIPS"):
                current_table = None
            elif current_table is not None and line.strip().startswith("- "):
                col_match = re.match(r"^\s*-\s*(\w+)\s*\(([^)]+)\)(?:\s*\[(.*?)\])?", line)
                if col_match:
                    cname, ctype, flags_str = col_match.groups()
                    flags = [f.strip() for f in flags_str.split(",")] if flags_str else []
                    fk_target = None
                    for f in flags:
                        if f.startswith("FK->"):
                            fk_target = f.replace("FK->", "")
                    current_table["columns"].append({
                        "name": cname,
                        "data_type": ctype,
                        "flags": flags,
                        "is_primary_key": "PK" in flags,
                        "is_unique": "UQ" in flags,
                        "is_not_null": "NN" in flags,
                        "is_foreign_key": fk_target is not None,
                        "foreign_key_target": fk_target,
                    })
            elif line.strip().startswith("- ") and current_table is None and "RELATIONSHIPS" not in line:
                rel_match = re.match(r"^\s*-\s*([\w.]+)\s*\[([^]]*)\]\s*([\w.]+)", line)
                if rel_match:
                    from_col, rel_type, to_col = rel_match.groups()
                    relationships.append({
                        "from": from_col,
                        "type": rel_type.strip(),
                        "to": to_col,
                    })
            elif current_table is None and len(tables) == 0 and line.strip():
                desc_lines.append(line.strip())

        return {
            "code": code,
            "title": f"Schema {code}",
            "description": " ".join(desc_lines),
            "raw_markdown": raw_markdown,
            "tables": tables,
            "relationships": relationships,
            "table_count": len(tables),
            "column_count": sum(len(t["columns"]) for t in tables),
            "relationship_count": len(relationships),
        }

    def list_schemas(self, evaluator_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return condition-blind list of schemas with optional evaluator rating status."""
        evaluations_by_code: Dict[str, ExpertEvaluation] = {}
        if evaluator_name:
            evaluator_name = evaluator_name.strip()
            with get_session() as session:
                rows = session.scalars(
                    select(ExpertEvaluation).where(ExpertEvaluation.evaluator_name == evaluator_name)
                ).all()
                for r in rows:
                    evaluations_by_code[r.schema_code] = r

        results = []
        for code, schema in sorted(self._schemas_cache.items()):
            item = {
                "code": schema["code"],
                "title": schema["title"],
                "description": schema["description"],
                "tables": schema["tables"],
                "relationships": schema["relationships"],
                "table_count": schema["table_count"],
                "column_count": schema["column_count"],
                "relationship_count": schema["relationship_count"],
                "raw_markdown": schema["raw_markdown"],
                "has_evaluated": code in evaluations_by_code,
            }
            if code in evaluations_by_code:
                ev = evaluations_by_code[code]
                item["rating"] = {
                    "d1_3nf": ev.d1_3nf,
                    "d2_naming": ev.d2_naming,
                    "d3_constraints": ev.d3_constraints,
                    "d4_relationships": ev.d4_relationships,
                    "d5_domain": ev.d5_domain,
                    "comment": ev.comment,
                    "updated_at": ev.updated_at.isoformat() if ev.updated_at else None,
                }
            results.append(item)
        return results

    def get_schema(self, code: str, evaluator_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get full details of a single schema."""
        if code not in self._schemas_cache:
            return None
        schema = self._schemas_cache[code]
        out = dict(schema)
        out["has_evaluated"] = False
        if evaluator_name:
            with get_session() as session:
                ev = session.scalars(
                    select(ExpertEvaluation).where(
                        ExpertEvaluation.evaluator_name == evaluator_name.strip(),
                        ExpertEvaluation.schema_code == code,
                    )
                ).first()
                if ev:
                    out["has_evaluated"] = True
                    out["rating"] = {
                        "d1_3nf": ev.d1_3nf,
                        "d2_naming": ev.d2_naming,
                        "d3_constraints": ev.d3_constraints,
                        "d4_relationships": ev.d4_relationships,
                        "d5_domain": ev.d5_domain,
                        "comment": ev.comment,
                        "updated_at": ev.updated_at.isoformat() if ev.updated_at else None,
                    }
        return out

    def save_evaluation(
        self,
        evaluator_name: str,
        schema_code: str,
        d1_3nf: int,
        d2_naming: int,
        d3_constraints: int,
        d4_relationships: int,
        d5_domain: int,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save or update an expert evaluation for a schema."""
        evaluator_name = evaluator_name.strip()
        schema_code = schema_code.strip().upper()
        if not evaluator_name:
            raise ValueError("evaluator_name is required")
        if schema_code not in self._schemas_cache:
            raise ValueError(f"Unknown schema code: {schema_code}")

        # Validate Likert 1-5
        for name, val in [
            ("d1_3nf", d1_3nf),
            ("d2_naming", d2_naming),
            ("d3_constraints", d3_constraints),
            ("d4_relationships", d4_relationships),
            ("d5_domain", d5_domain),
        ]:
            if not isinstance(val, int) or val < 1 or val > 5:
                raise ValueError(f"{name} must be an integer between 1 and 5")

        with get_session() as session:
            existing = session.scalars(
                select(ExpertEvaluation).where(
                    ExpertEvaluation.evaluator_name == evaluator_name,
                    ExpertEvaluation.schema_code == schema_code,
                )
            ).first()

            now = datetime.now(timezone.utc)
            if existing:
                existing.d1_3nf = d1_3nf
                existing.d2_naming = d2_naming
                existing.d3_constraints = d3_constraints
                existing.d4_relationships = d4_relationships
                existing.d5_domain = d5_domain
                existing.comment = comment.strip() if comment else None
                existing.updated_at = now
                ev_id = existing.id
            else:
                ev_id = str(uuid.uuid4())
                new_eval = ExpertEvaluation(
                    id=ev_id,
                    evaluator_name=evaluator_name,
                    schema_code=schema_code,
                    d1_3nf=d1_3nf,
                    d2_naming=d2_naming,
                    d3_constraints=d3_constraints,
                    d4_relationships=d4_relationships,
                    d5_domain=d5_domain,
                    comment=comment.strip() if comment else None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_eval)

            session.commit()

        return {
            "id": ev_id,
            "evaluator_name": evaluator_name,
            "schema_code": schema_code,
            "d1_3nf": d1_3nf,
            "d2_naming": d2_naming,
            "d3_constraints": d3_constraints,
            "d4_relationships": d4_relationships,
            "d5_domain": d5_domain,
            "comment": comment,
            "status": "saved",
        }

    def get_evaluations_by_evaluator(self, evaluator_name: str) -> List[Dict[str, Any]]:
        """Return all evaluations submitted by a specific evaluator."""
        with get_session() as session:
            rows = session.scalars(
                select(ExpertEvaluation).where(ExpertEvaluation.evaluator_name == evaluator_name.strip())
            ).all()
            return [
                {
                    "schema_code": r.schema_code,
                    "d1_3nf": r.d1_3nf,
                    "d2_naming": r.d2_naming,
                    "d3_constraints": r.d3_constraints,
                    "d4_relationships": r.d4_relationships,
                    "d5_domain": r.d5_domain,
                    "comment": r.comment,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]

    def verify_admin_key(self, key: str) -> bool:
        """Verify admin password or key against configured admin_secret_key."""
        expected = (settings.admin_secret_key or "admin123").strip()
        return bool(key and key.strip() == expected)

    def get_admin_dashboard_data(self) -> Dict[str, Any]:
        """Compile unblinded evaluations and research statistics for admin view."""
        with get_session() as session:
            rows = session.scalars(select(ExpertEvaluation).order_by(ExpertEvaluation.updated_at.desc())).all()

        total_schemas = len(self._schemas_cache) or 30
        evaluations_list: List[Dict[str, Any]] = []
        evaluators_set = set()
        evaluator_counts: Dict[str, int] = {}

        # Aggregation buckets
        all_scores: Dict[str, List[int]] = {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []}
        by_condition: Dict[str, Dict[str, List[int]]] = {
            "baseline": {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []},
            "full_llm": {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []},
        }
        by_dataset: Dict[str, Dict[str, List[int]]] = {
            "hospital": {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []},
            "library": {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []},
            "university": {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []},
        }

        for r in rows:
            evaluators_set.add(r.evaluator_name)
            evaluator_counts[r.evaluator_name] = evaluator_counts.get(r.evaluator_name, 0) + 1

            meta = self._mapping_cache.get(r.schema_code, {"dataset": "unknown", "condition": "unknown", "run": "unknown"})
            record = {
                "id": r.id,
                "evaluator_name": r.evaluator_name,
                "schema_code": r.schema_code,
                "dataset": meta.get("dataset"),
                "condition": meta.get("condition"),
                "run": meta.get("run"),
                "d1_3nf": r.d1_3nf,
                "d2_naming": r.d2_naming,
                "d3_constraints": r.d3_constraints,
                "d4_relationships": r.d4_relationships,
                "d5_domain": r.d5_domain,
                "average_score": round((r.d1_3nf + r.d2_naming + r.d3_constraints + r.d4_relationships + r.d5_domain) / 5.0, 2),
                "comment": r.comment or "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            evaluations_list.append(record)

            # Record scores for aggregation
            all_scores["d1"].append(r.d1_3nf)
            all_scores["d2"].append(r.d2_naming)
            all_scores["d3"].append(r.d3_constraints)
            all_scores["d4"].append(r.d4_relationships)
            all_scores["d5"].append(r.d5_domain)

            cond = meta.get("condition")
            if cond in by_condition:
                by_condition[cond]["d1"].append(r.d1_3nf)
                by_condition[cond]["d2"].append(r.d2_naming)
                by_condition[cond]["d3"].append(r.d3_constraints)
                by_condition[cond]["d4"].append(r.d4_relationships)
                by_condition[cond]["d5"].append(r.d5_domain)

            ds = meta.get("dataset")
            if ds in by_dataset:
                by_dataset[ds]["d1"].append(r.d1_3nf)
                by_dataset[ds]["d2"].append(r.d2_naming)
                by_dataset[ds]["d3"].append(r.d3_constraints)
                by_dataset[ds]["d4"].append(r.d4_relationships)
                by_dataset[ds]["d5"].append(r.d5_domain)

        def _calc_means(scores_dict: Dict[str, List[int]]) -> Dict[str, Any]:
            count = len(scores_dict.get("d1", []))
            if count == 0:
                return {"count": 0, "d1_3nf": 0, "d2_naming": 0, "d3_constraints": 0, "d4_relationships": 0, "d5_domain": 0, "overall": 0}
            d1 = sum(scores_dict["d1"]) / count
            d2 = sum(scores_dict["d2"]) / count
            d3 = sum(scores_dict["d3"]) / count
            d4 = sum(scores_dict["d4"]) / count
            d5 = sum(scores_dict["d5"]) / count
            return {
                "count": count,
                "d1_3nf": round(d1, 2),
                "d2_naming": round(d2, 2),
                "d3_constraints": round(d3, 2),
                "d4_relationships": round(d4, 2),
                "d5_domain": round(d5, 2),
                "overall": round((d1 + d2 + d3 + d4 + d5) / 5.0, 2),
            }

        evaluator_progress = [
            {
                "evaluator_name": name,
                "completed": cnt,
                "total": total_schemas,
                "progress_percent": round((cnt / total_schemas) * 100, 1),
            }
            for name, cnt in sorted(evaluator_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Per-schema review status
        schema_summary = []
        for code in sorted(self._schemas_cache.keys()):
            meta = self._mapping_cache.get(code, {})
            code_evals = [e for e in evaluations_list if e["schema_code"] == code]
            schema_summary.append({
                "code": code,
                "dataset": meta.get("dataset", "unknown"),
                "condition": meta.get("condition", "unknown"),
                "run": meta.get("run", "unknown"),
                "evaluations_count": len(code_evals),
                "avg_score": round(sum(e["average_score"] for e in code_evals) / len(code_evals), 2) if code_evals else None,
            })

        return {
            "total_schemas": total_schemas,
            "total_evaluations": len(rows),
            "unique_evaluators_count": len(evaluators_set),
            "evaluator_progress": evaluator_progress,
            "overall_means": _calc_means(all_scores),
            "condition_comparison": {
                "baseline": _calc_means(by_condition["baseline"]),
                "full_llm": _calc_means(by_condition["full_llm"]),
            },
            "dataset_comparison": {
                "hospital": _calc_means(by_dataset["hospital"]),
                "library": _calc_means(by_dataset["library"]),
                "university": _calc_means(by_dataset["university"]),
            },
            "schema_summary": schema_summary,
            "evaluations": evaluations_list,
        }

    def export_csv(self) -> str:
        """Export evaluations as CSV matching research schema."""
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow([
            "evaluator",
            "code",
            "dataset",
            "condition",
            "run",
            "d1_3nf",
            "d2_naming",
            "d3_constraints",
            "d4_relationships",
            "d5_domain",
            "comment",
            "updated_at",
        ])

        with get_session() as session:
            rows = session.scalars(select(ExpertEvaluation).order_by(ExpertEvaluation.evaluator_name, ExpertEvaluation.schema_code)).all()
            for r in rows:
                meta = self._mapping_cache.get(r.schema_code, {})
                writer.writerow([
                    r.evaluator_name,
                    r.schema_code,
                    meta.get("dataset", ""),
                    meta.get("condition", ""),
                    meta.get("run", ""),
                    r.d1_3nf,
                    r.d2_naming,
                    r.d3_constraints,
                    r.d4_relationships,
                    r.d5_domain,
                    r.comment or "",
                    r.updated_at.isoformat() if r.updated_at else "",
                ])

        return out.getvalue()


# Singleton instance
expert_service = ExpertEvaluationService()
