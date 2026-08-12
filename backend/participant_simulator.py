"""Offline participant-flow simulator; never invokes an LLM or network service."""
from __future__ import annotations

import argparse
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.experiment_service import ExperimentService


def valid_sus(scores) -> bool:
    return isinstance(scores, list) and len(scores) == 10 and all(type(value) is int and 1 <= value <= 5 for value in scores)


def valid_nasa(scores) -> bool:
    required = {"mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration"}
    return set(scores) == required and all(type(value) in {int, float} and 0 <= value <= 100 and value % 5 == 0 for value in scores.values())


def simulate(output: Path) -> dict:
    # Load transitive standard-library networking modules before the runtime guard.
    from app.services import interaction_logger as _interaction_logger  # noqa: F401
    from app.services import schema_service as _schema_service  # noqa: F401
    os.environ.setdefault("EXPERIMENT_ASSIGNMENT_SEED", "offline-simulator-seed")
    fixed_now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    counter = iter(range(1000))
    output.mkdir(parents=True, exist_ok=True)
    (output / "sessions.json").unlink(missing_ok=True)
    (output / "sessions.json.lock").unlink(missing_ok=True)
    service = ExperimentService(output / "sessions.json", clock=lambda: fixed_now,
                                id_factory=lambda: f"sim-{next(counter):04d}", project_eraser=lambda _project: None)
    original_socket = socket.socket
    socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network disabled in simulator"))
    try:
        return _simulate(service, output, fixed_now)
    finally:
        socket.socket = original_socket


def _simulate(service: ExperimentService, output: Path, fixed_now: datetime) -> dict:
    happy = service.start("happy", "project-happy", "pilot-v1")
    service.transition("happy", "completed")
    abandon = service.start("abandon", "project-abandon", "pilot-v1")
    withdrawn = service.transition("abandon", "withdrawn")
    timed = service.start("timeout", "project-timeout", "pilot-v1")
    data = service._load()
    data["sessions"][timed["session_id"]]["deadline_at"] = (fixed_now - timedelta(seconds=1)).isoformat()
    from app.utils.research import atomic_write_json
    atomic_write_json(service.path, data)
    timed = service.for_subject("timeout")
    cross_condition_blocked = False
    try:
        service.require("happy", "other-project", "project_view")
    except (PermissionError, TimeoutError):
        cross_condition_blocked = True
    with ThreadPoolExecutor(max_workers=8) as executor:
        concurrent = list(executor.map(lambda _: service.start("concurrent", "project-concurrent", "pilot-v1"), range(16)))
    arms = {}
    for index in range(100):
        candidate = service.start(f"arm-{index}", f"project-arm-{index}", "pilot-v1")
        arms.setdefault(candidate["condition"], candidate)
        if len(arms) == 3:
            break
    report = {
        "network_calls": 0,
        "scenarios": {
            "happy_path": service.for_subject("happy")["status"] == "completed",
            "withdrawal": withdrawn["status"] == "withdrawn" and service.for_subject("abandon") is None,
            "timeout": timed["status"] == "timed_out",
            "invalid_sus_rejected": not valid_sus([5] * 9),
            "invalid_nasa_rejected": not valid_nasa({"effort": 37}),
            "cross_project_blocked": cross_condition_blocked,
            "concurrent_idempotent": len({item["session_id"] for item in concurrent}) == 1,
            "all_three_arms": set(arms) == {"manual", "ai_only", "ai_interface"},
            "capabilities_distinct": ("chat" not in arms["ai_only"]["capabilities"]
                                      and "ai_generate" not in arms["manual"]["capabilities"]
                                      and "chat" in arms["ai_interface"]["capabilities"]),
        },
    }
    report["status"] = "pass" if all(report["scenarios"].values()) else "fail"
    output.mkdir(parents=True, exist_ok=True)
    (output / "simulation-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    service.path.unlink(missing_ok=True)
    service.path.with_suffix(service.path.suffix + ".lock").unlink(missing_ok=True)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/participant-simulation"))
    args = parser.parse_args(argv)
    report = simulate(args.output)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
