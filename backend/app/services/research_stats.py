"""Statistiche semplici per i confronti dei run: media con intervallo bootstrap (nessuna dipendenza)."""
from __future__ import annotations

import random
from statistics import mean
from typing import Iterable

BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20240601  # fisso: lo stesso insieme di run da' sempre gli stessi intervalli


def bootstrap_ci(values: Iterable[float | None], confidence: float = 0.95,
                 resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED) -> dict:
    """Media e intervallo percentile bootstrap. Con un solo valore l'intervallo coincide con la media."""
    data = [float(v) for v in values if v is not None]
    if not data:
        return {"n": 0, "mean": None, "low": None, "high": None}
    avg = mean(data)
    if len(data) == 1:
        return {"n": 1, "mean": round(avg, 4), "low": round(avg, 4), "high": round(avg, 4)}
    rng = random.Random(seed)
    n = len(data)
    means = sorted(mean(rng.choices(data, k=n)) for _ in range(resamples))
    alpha = (1 - confidence) / 2
    low = means[int(alpha * (resamples - 1))]
    high = means[int((1 - alpha) * (resamples - 1))]
    return {"n": n, "mean": round(avg, 4), "low": round(low, 4), "high": round(high, 4)}


def safe_mean(values: Iterable[float | None]) -> float | None:
    data = [float(v) for v in values if v is not None]
    return round(mean(data), 4) if data else None
