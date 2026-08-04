"""Dynamic LLM adjudication of a generated database against the gold standard.

Offers a supplementary, qualitative check that complements the deterministic
cell-level metrics (see docs/11-benchmark-protocol.md section 6.4). The LLM-as-
judge compares the generated schema and a compact dump of the generated data
against the gold schema and ground truth, scoring three fixed dimensions on a
0-100 scale:

1. ``schema_equivalence``  — do the generated tables/columns/constraints model
   the same information as the gold schema, up to naming/structuring?
2. ``value_accuracy``      — do the generated values match the ground truth for
   the corresponding entities/rows?
3. ``completeness``        — how much of the gold data is represented (missing
   rows/entities reduce the score)?

The rubric, output schema and (where applicable) a prompting seed are fixed so
the call is reproducible. Provenance (provider/model, hashes, temperature) is
recorded alongside the scores. This metric is *supplementary*: it never replaces
the deterministic F1, and it is subject to the same-model self-evaluation bias
and therefore clearly labelled as such in the reported output.
"""
from __future__ import annotations

import json
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from typing import Any

from app.core.llm import _get_llm, get_llm_run_metadata
from app.models.schema_models import NormalizedSchema
from app.utils.logger import log
from app.utils.research import sha256_text

# Fixed rubric: dimension -> human-readable criterion. Kept versioned so that a
# change in adjudication semantics is a deliberate, documented act.
ADJUDICATION_RUBRIC = {
    "schema_equivalence": (
        "Do the generated tables, columns and constraints model the same "
        "information as the gold schema, allowing equivalent renaming and "
        "re-structuring? Pure naming divergence should score HIGH."
    ),
    "value_accuracy": (
        "For the data that IS present, do the generated values match the "
        "ground-truth values of the corresponding entities/rows?"
    ),
    "completeness": (
        "How much of the gold-standard data is represented in the generated "
        "database? Missing rows/entities lower this score."
    ),
}

ADJUDICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an impartial database-quality adjudicator. You compare a
GENERATED database against a GOLD-STANDARD reference for a database-automation
research benchmark.

Score all three dimensions on a 0-100 integer scale, where 100 is "perfect".
Be strict and specific. Distinguish semantic equivalence (same information,
possibly different names/structure) from genuine error.

Respond ONLY with a JSON object of the exact shape:
{{"schema_equivalence": <int 0-100>, "value_accuracy": <int 0-100>,
  "completeness": <int 0-100>, "notes": "<short justification>"}}

Your output must be valid JSON with no markdown fences or extra text."""),
    ("user", """ADJUDICATION RUBRIC:
1. schema_equivalence: {schema_equivalence}
2. value_accuracy: {value_accuracy}
3. completeness: {completeness}

=== GOLD SCHEMA ===
{gold_schema}

=== GENERATED SCHEMA ===
{generated_schema}

=== GROUND TRUTH (first rows per table) ===
{ground_rows}

=== GENERATED DATA (first rows per table, aligned to gold) ===
{generated_rows}

{format_instructions}"""),
])


def _dump_schema(schema: NormalizedSchema) -> str:
    parts = []
    for table in schema.tables:
        cols = []
        for c in table.columns:
            label = f"{c.name} {c.data_type}"
            if c.is_primary_key:
                label += " PK"
            if c.is_foreign_key:
                label += f" FK->{c.foreign_key_table}.{c.foreign_key_column}"
            if c.is_not_null:
                label += " NOT NULL"
            cols.append(label)
        parts.append(f"{table.name}:\n  - " + "\n  - ".join(cols))
    return "\n".join(parts)


def _rows_to_text(table_name: str, rows: list[dict], limit: int = 12) -> str:
    if not rows:
        return f"{table_name}: (empty)"
    lines = []
    for row in rows[:limit]:
        lines.append("  | ".join(f"{k}={v}" for k, v in row.items()))
    body = "\n".join(lines) if lines else "(no columns)"
    return f"{table_name} ({len(rows)} rows total, showing {min(limit, len(rows))}):\n{body}"


def _compact_row_report(per_table: dict[str, list[dict]]) -> str:
    parts = []
    for table_name, rows in per_table.items():
        parts.append(_rows_to_text(table_name, rows))
    return "\n\n".join(parts)


async def _invoke_chain(prompt_values: dict) -> dict:
    """Run the adjudication prompt through the LLM and a JSON parser.

    Split out so tests can substitute a fake chain without building the real
    LangChain composition (which would require an LLM endpoint).
    """
    parser = JsonOutputParser()
    llm = _get_llm(temperature=0.0)
    chain = ADJUDICATION_PROMPT | llm | parser
    from app.core.llm import _invoke
    return await _invoke(chain, {**prompt_values,
                                 "format_instructions": parser.get_format_instructions()})


async def adjudicate(schema: NormalizedSchema, generated_schema: NormalizedSchema,
                     ground_rows: dict[str, list[dict]],
                     generated_rows: dict[str, list[dict]]) -> dict:
    """Run the LLM-as-judge comparison and return scores plus provenance."""
    prompt_values = {
        "schema_equivalence": ADJUDICATION_RUBRIC["schema_equivalence"],
        "value_accuracy": ADJUDICATION_RUBRIC["value_accuracy"],
        "completeness": ADJUDICATION_RUBRIC["completeness"],
        "gold_schema": _dump_schema(schema),
        "generated_schema": _dump_schema(generated_schema),
        "ground_rows": _compact_row_report(ground_rows),
        "generated_rows": _compact_row_report(generated_rows),
    }
    try:
        result = await _invoke_chain(prompt_values)
    except Exception as exc:
        log.warning(f"LLM adjudication failed ({type(exc).__name__})")
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "scores": None,
            "notes": None,
        }

    if not isinstance(result, dict):
        log.warning("LLM adjudication returned no usable result")
        return {
            "status": "error",
            "error": "adjudication returned a non-dict result",
            "scores": None,
            "notes": None,
        }

    scores = {
        key: result.get(key) for key in ADJUDICATION_RUBRIC
    }
    scores = {k: (int(v) if v is not None else None) for k, v in scores.items()}
    return {
        "status": "ok",
        "scores": scores,
        "notes": result.get("notes"),
        "metadata": get_llm_run_metadata(0.0, "adjudication_rubric_v1"),
        "rubric_version": "adjudication_rubric_v1",
        "rubric_hash": sha256_text(json.dumps(ADJUDICATION_RUBRIC, sort_keys=True)),
    }