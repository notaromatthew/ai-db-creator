"""Versioned candidate blocked allocation; never represents protocol approval."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
from pathlib import Path

from app.utils.research import stable_hash


CONFIG_PATH = Path(__file__).resolve().parents[2] / "research_configs" / "allocation-candidate-v1.json"


class CandidateAllocator:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        if self.config.get("status") != "candidate_unapproved":
            raise ValueError("allocation configuration must remain explicitly unapproved")
        self.config_hash = stable_hash(self.config)

    def assign(self, assignments: list[dict], dataset_id: str, experience_stratum: str) -> tuple[str, dict]:
        if not dataset_id or not dataset_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("dataset_id must be a controlled identifier")
        if experience_stratum not in self.config["allowed_experience_strata"]:
            raise ValueError("experience_stratum is not allowed by allocation config")
        seed = os.getenv(self.config["seed_environment_variable"])
        if not seed:
            raise RuntimeError("allocation seed must be supplied only through the configured environment variable")
        stratum = f"{dataset_id}:{experience_stratum}"
        prior = [item for item in assignments if item.get("allocation_stratum") == stratum]
        index = len(prior)
        block_sizes = self.config["block_sizes"]
        block_number = 0
        block_start = 0
        while True:
            size_seed = hmac.new(seed.encode(), f"{self.config_hash}:{stratum}:size:{block_number}".encode(), hashlib.sha256).digest()
            block_size = block_sizes[random.Random(int.from_bytes(size_seed, "big")).randrange(len(block_sizes))]
            if index < block_start + block_size:
                offset = index - block_start
                break
            block_start += block_size
            block_number += 1
        block_seed = hmac.new(seed.encode(), f"{self.config_hash}:{stratum}:{block_number}:{block_size}".encode(), hashlib.sha256).digest()
        sequence = list(self.config["arms"]) * (block_size // len(self.config["arms"]))
        random.Random(int.from_bytes(block_seed, "big")).shuffle(sequence)
        condition = sequence[offset]
        audit = {"allocation_config_version": self.config["schema_version"], "allocation_config_hash": self.config_hash,
                 "allocation_stratum": stratum, "dataset_id": dataset_id, "experience_stratum": experience_stratum,
                 "block_number": block_number, "position_in_block": offset, "assignment_method": "stratified_permuted_block_candidate",
                 "approval_status": "human_approval_missing"}
        return condition, audit
