"""Legacy telemetry analysis retained for prior protocol revisions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.cluster.vq import kmeans2
from scipy.spatial.distance import cdist


ARMS = ("manual", "ai_only", "ai_interface")
PRIMARY_METRICS = ("schema_quality", "residual_error_rate")
SECONDARY_METRICS = ("task_time_seconds",)
CONTRASTS = (
    ("RQ0", "manual", "ai_interface"),
    ("RQ3", "ai_only", "ai_interface"),
)


class AnalysisError(ValueError):
    pass


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fields = set(rows[0]) if rows else set()
    missing = required - fields
    if missing:
        raise AnalysisError(f"{path.name}: colonne mancanti: {', '.join(sorted(missing))}")
    return rows


def _bool(value: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "si", "sì"}:
        return True
    if normalized in {"false", "0", "no", ""}:
        return False
    raise AnalysisError(f"Valore booleano non valido: {value!r}")


def _float(value: str, name: str, low: float | None = None, high: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AnalysisError(f"{name}: valore numerico non valido: {value!r}") from exc
    if not math.isfinite(result) or low is not None and result < low or high is not None and result > high:
        raise AnalysisError(f"{name}: valore fuori intervallo: {value!r}")
    return result


def _iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnalysisError(f"Timestamp ISO 8601 non valido: {value!r}") from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def holm_adjust(p_values: list[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, (index, value) in enumerate(indexed):
        running = max(running, min(1.0, value * (total - rank)))
        adjusted[index] = running
    return adjusted


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1], reverse=True)
    adjusted = [1.0] * len(p_values)
    running = 1.0
    total = len(p_values)
    for reverse_rank, (index, value) in enumerate(indexed):
        rank = total - reverse_rank
        running = min(running, value * total / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def _mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def _cohen_d(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return math.nan
    variance = ((len(left) - 1) * statistics.variance(left) + (len(right) - 1) * statistics.variance(right)) / (len(left) + len(right) - 2)
    return (statistics.mean(right) - statistics.mean(left)) / math.sqrt(variance) if variance > 0 else 0.0


def _welch_p(left: list[float], right: list[float]) -> float:
    if statistics.pvariance(left) == 0 and statistics.pvariance(right) == 0:
        return 1.0 if statistics.mean(left) == statistics.mean(right) else 0.0
    return float(stats.ttest_ind(left, right, equal_var=False).pvalue)


def _bootstrap_difference(left: list[float], right: list[float], rng: random.Random, resamples: int) -> tuple[float, float]:
    differences = []
    for _ in range(resamples):
        sample_left = [rng.choice(left) for _ in left]
        sample_right = [rng.choice(right) for _ in right]
        differences.append(statistics.mean(sample_right) - statistics.mean(sample_left))
    differences.sort()
    return differences[int(0.025 * resamples)], differences[min(resamples - 1, int(0.975 * resamples))]


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _participant_metrics(participants_path: Path, events_path: Path, outcomes_path: Path) -> tuple[list[dict], dict[str, list[str]]]:
    participants = _read_csv(participants_path, {
        "participant_id", "arm", "completed", "withdrawn",
    })
    events = _read_csv(events_path, {"participant_id", "arm", "type", "created_at", "data"})
    outcomes = _read_csv(outcomes_path, {
        "participant_id", "dataset", "schema_quality", "residual_error_rate", "task_success",
    })
    ids = [row["participant_id"].strip() for row in participants]
    if not all(ids) or len(ids) != len(set(ids)):
        raise AnalysisError("participants.csv contiene ID vuoti o duplicati")
    outcome_by_id = {row["participant_id"].strip(): row for row in outcomes}
    if len(outcome_by_id) != len(outcomes):
        raise AnalysisError("outcomes.csv contiene participant_id duplicati")
    event_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in events:
        event_by_id[row["participant_id"].strip()].append(row)
    metrics = []
    sequences: dict[str, list[str]] = {}
    for participant in participants:
        pid = participant["participant_id"].strip()
        arm = participant["arm"].strip()
        if arm not in ARMS:
            raise AnalysisError(f"{pid}: braccio non valido: {arm!r}")
        if _bool(participant["withdrawn"]) or not _bool(participant["completed"]):
            continue
        if pid not in outcome_by_id:
            raise AnalysisError(f"{pid}: outcome finale mancante")
        outcome = outcome_by_id[pid]
        task_success = _bool(outcome["task_success"])
        ordered = sorted(event_by_id.get(pid, []), key=lambda row: _iso(row["created_at"]))
        starts = [_iso(row["created_at"]) for row in ordered if row["type"] == "task_start"]
        ends = [_iso(row["created_at"]) for row in ordered if row["type"] == "task_end"]
        if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
            raise AnalysisError(f"{pid}: servono esattamente un task_start e un task_end validi")
        sequence = [row["type"].strip() for row in ordered if row["type"].strip()]
        sequences[pid] = sequence
        counts = Counter(sequence)
        metrics.append({
            "participant_id": pid,
            "arm": arm,
            "dataset": outcome["dataset"].strip(),
            "schema_quality": _float(outcome["schema_quality"], "schema_quality", 1, 5),
            "residual_error_rate": _float(outcome["residual_error_rate"], "residual_error_rate", 0, 1),
            "task_success": int(task_success),
            "task_time_seconds": (ends[0] - starts[0]).total_seconds(),
            **{f"event_{name}": count for name, count in sorted(counts.items())},
        })
    if not metrics:
        raise AnalysisError("Nessun partecipante completato e non ritirato")
    for arm in ARMS:
        if not any(row["arm"] == arm for row in metrics):
            raise AnalysisError(f"Nessun caso completo nel braccio {arm}")
    return metrics, sequences


def _descriptives(metrics: list[dict]) -> list[dict]:
    rows = []
    for arm in ARMS:
        group = [row for row in metrics if row["arm"] == arm]
        result = {"arm": arm, "n": len(group), "task_success_rate": statistics.mean(row["task_success"] for row in group)}
        for metric in (*PRIMARY_METRICS, *SECONDARY_METRICS):
            mean, sd = _mean_sd([row[metric] for row in group])
            result[f"{metric}_mean"] = mean
            result[f"{metric}_sd"] = sd
        rows.append(result)
    return rows


def _contrasts(metrics: list[dict], seed: int, resamples: int) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for rq, left_arm, right_arm in CONTRASTS:
        for metric in (*PRIMARY_METRICS, *SECONDARY_METRICS):
            left = [row[metric] for row in metrics if row["arm"] == left_arm]
            right = [row[metric] for row in metrics if row["arm"] == right_arm]
            low, high = _bootstrap_difference(left, right, rng, resamples)
            mann = stats.mannwhitneyu(left, right, alternative="two-sided")
            rows.append({
                "rq": rq,
                "metric": metric,
                "family": "confirmatory" if metric in PRIMARY_METRICS else "secondary",
                "left_arm": left_arm,
                "right_arm": right_arm,
                "n_left": len(left),
                "n_right": len(right),
                "mean_left": statistics.mean(left),
                "mean_right": statistics.mean(right),
                "difference_right_minus_left": statistics.mean(right) - statistics.mean(left),
                "bootstrap_ci_low": low,
                "bootstrap_ci_high": high,
                "cohen_d": _cohen_d(left, right),
                "welch_p": _welch_p(left, right),
                "mann_whitney_p": float(mann.pvalue),
                "holm_p": "",
            })
    primary_indexes = [index for index, row in enumerate(rows) if row["family"] == "confirmatory"]
    adjusted = holm_adjust([rows[index]["welch_p"] for index in primary_indexes])
    for index, value in zip(primary_indexes, adjusted):
        rows[index]["holm_p"] = value
    return rows


def _prefixspan(sequences: list[list[str]], min_support: float, max_length: int = 5) -> list[dict]:
    threshold = max(1, math.ceil(min_support * len(sequences)))
    output: list[dict] = []

    def grow(prefix: tuple[str, ...], projected: list[list[str]]) -> None:
        candidates = Counter()
        for sequence in projected:
            candidates.update(set(sequence))
        for item, support_count in sorted(candidates.items()):
            if support_count < threshold:
                continue
            pattern = (*prefix, item)
            next_projected = []
            for sequence in projected:
                try:
                    position = sequence.index(item)
                except ValueError:
                    continue
                next_projected.append(sequence[position + 1:])
            if len(pattern) >= 2:
                output.append({"pattern": " > ".join(pattern), "support_count": support_count, "support": support_count / len(sequences)})
            if len(pattern) < max_length:
                grow(pattern, next_projected)

    grow(tuple(), sequences)
    return sorted(output, key=lambda row: (-row["support"], row["pattern"]))


def _rq4(metrics: list[dict], sequences: dict[str, list[str]]) -> tuple[list[dict], list[dict], list[dict]]:
    group = [row for row in metrics if row["arm"] == "ai_interface"]
    event_fields = sorted({key for row in group for key in row if key.startswith("event_")})
    correlations = []
    for field in event_fields:
        x = [float(row.get(field, 0)) for row in group]
        if len(set(x)) < 2:
            continue
        result = stats.spearmanr(x, [row["schema_quality"] for row in group])
        correlations.append({"feature": field, "spearman_rho": float(result.statistic), "p": float(result.pvalue), "fdr_p": ""})
    if correlations:
        for row, adjusted in zip(correlations, benjamini_hochberg([row["p"] for row in correlations])):
            row["fdr_p"] = adjusted
    patterns = _prefixspan([sequences[row["participant_id"]] for row in group], 0.3)
    clusters = []
    if len(group) >= 6 and len(event_fields) >= 2:
        matrix = np.array([[float(row.get(field, 0)) for field in event_fields] for row in group], dtype=float)
        std = matrix.std(axis=0)
        keep = std > 0
        matrix = matrix[:, keep]
        selected_fields = [field for field, include in zip(event_fields, keep) if include]
        unique_rows = len(np.unique(matrix, axis=0))
        if matrix.shape[1] >= 2 and unique_rows >= 3:
            matrix = (matrix - matrix.mean(axis=0)) / matrix.std(axis=0)
            best = None
            for k in range(3, min(5, len(group) - 1, unique_rows) + 1):
                centroids, labels = kmeans2(matrix, k, minit="++", seed=20261103)
                distances = cdist(matrix, matrix)
                silhouettes = []
                for index, label in enumerate(labels):
                    same = [i for i, item in enumerate(labels) if item == label and i != index]
                    other_labels = set(labels) - {label}
                    if not same or not other_labels:
                        silhouettes.append(0.0)
                        continue
                    a = float(np.mean(distances[index, same]))
                    b = min(float(np.mean(distances[index, [i for i, item in enumerate(labels) if item == other]])) for other in other_labels)
                    silhouettes.append((b - a) / max(a, b) if max(a, b) else 0.0)
                score = statistics.mean(silhouettes)
                if best is None or score > best[0]:
                    best = (score, k, centroids, labels)
            if best:
                score, k, centroids, labels = best
                for row, label in zip(group, labels):
                    clusters.append({
                        "participant_id": row["participant_id"],
                        "cluster": int(label) + 1,
                        "k": k,
                        "silhouette": score,
                        "features": "|".join(selected_fields),
                    })
    return patterns, correlations, clusters


def analyze(participants: Path, events: Path, outcomes: Path, output: Path, seed: int, resamples: int) -> dict:
    if resamples < 100:
        raise AnalysisError("Servono almeno 100 ricampionamenti bootstrap")
    metrics, sequences = _participant_metrics(participants, events, outcomes)
    descriptives = _descriptives(metrics)
    contrasts = _contrasts(metrics, seed, resamples)
    patterns, correlations, clusters = _rq4(metrics, sequences)
    output.mkdir(parents=True, exist_ok=True)
    metric_fields = ["participant_id", "arm", "dataset", *PRIMARY_METRICS, "task_success", *SECONDARY_METRICS]
    event_fields = sorted({key for row in metrics for key in row if key.startswith("event_")})
    _write_csv(output / "participant_metrics.csv", metrics, [*metric_fields, *event_fields])
    _write_csv(output / "arm_descriptives.csv", descriptives, list(descriptives[0]))
    _write_csv(output / "confirmatory_contrasts.csv", contrasts, list(contrasts[0]))
    _write_csv(output / "rq4_patterns.csv", patterns, ["pattern", "support_count", "support"])
    _write_csv(output / "rq4_correlations.csv", correlations, ["feature", "spearman_rho", "p", "fdr_p"])
    _write_csv(output / "rq4_clusters.csv", clusters, ["participant_id", "cluster", "k", "silhouette", "features"])
    manifest = {
        "artifact_status": "observed_analysis",
        "inputs": {path.name: _sha256(path) for path in (participants, events, outcomes)},
        "analysis_script_sha256": _sha256(Path(__file__)),
        "seed": seed,
        "bootstrap_resamples": resamples,
        "complete_nonwithdrawn_participants": len(metrics),
        "arm_counts": dict(Counter(row["arm"] for row in metrics)),
        "confirmatory_contrasts": [f"{rq}: {left} vs {right}" for rq, left, right in CONTRASTS],
        "primary_metrics": list(PRIMARY_METRICS),
        "secondary_metrics": list(SECONDARY_METRICS),
        "questionnaires_collected": False,
        "multiplicity": "Holm across the four preregistered contrast-by-primary-metric Welch tests",
        "rq4_multiplicity": "Benjamini-Hochberg across event-count correlations",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = [
        "# Analisi RQ0/RQ3/RQ4",
        "",
        f"Casi completi e non ritirati: **{len(metrics)}**.",
        "",
        "## Bracci",
        "",
        *[f"- `{arm}`: {manifest['arm_counts'].get(arm, 0)}" for arm in ARMS],
        "",
        "## Analisi confermativa",
        "",
        "I contrasti congelati sono Manuale vs AI + Interfaccia (RQ0) e AI-Only vs AI + Interfaccia (RQ3).",
        "La famiglia primaria comprende qualità dello schema e tasso di errori residui; i quattro p-value Welch sono corretti con Holm.",
        "Il tempo di completamento è riportato come outcome secondario. Il protocollo corrente non raccoglie questionari di carico cognitivo o usabilità.",
        "",
        "## RQ4",
        "",
        "Pattern sequenziali con supporto minimo 0,30, correlazioni di Spearman con correzione FDR e clustering esplorativo k=3..5 sono esportati separatamente.",
        "",
        "Il rapporto non sostituisce la verifica umana di protocollo, esclusioni, deviazioni, eleggibilità e interpretazione causale.",
    ]
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participants", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--bootstrap-resamples", type=int, default=5000)
    args = parser.parse_args()
    manifest = analyze(args.participants, args.events, args.outcomes, args.output, args.seed, args.bootstrap_resamples)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
