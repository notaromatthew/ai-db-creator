# RQ1 Expert Rating Pack — DRAFT / UNAPPROVED

> Template only. No experts have been recruited, trained or approved. Final materials require protocol and ethics/governance review where applicable.

## Blind review workflow

1. Coordinator freezes artifact hashes, rubric version and randomisation seed.
2. A separate mapping file links blinded `artifact_id` to run/condition; raters cannot access it.
3. Three qualified raters receive the same unrelated-domain calibration example.
4. Raters score independently and cannot discuss artifacts before lock.
5. Ratings are locked before condition labels and automated outcomes are revealed.
6. Missing ratings and protocol deviations are recorded, never silently filled.

## Qualification and calibration record

Record database-design experience, conflict of interest, training completion and calibration date using non-identifying rater IDs. Qualification threshold: `[freeze]`. Calibration uses examples excluded from the study. Clarify rubric wording rather than training raters toward a desired score. Pilot agreement does not count as confirmatory agreement.

## Rubric

Use D1–D5 anchors from `docs/11-benchmark-protocol.md`: 3NF compliance, naming quality, constraint coverage, relationship accuracy and domain alignment. Scores are ordinal 1–5. A score below 3 requires a controlled reason code; comments must not speculate about condition or model.

Reason codes: `NF_PARTIAL_DEPENDENCY`, `NF_TRANSITIVE_DEPENDENCY`, `MISSING_ENTITY`, `REDUNDANT_ENTITY`, `MISSING_PK`, `MISSING_OR_WRONG_FK`, `WRONG_CARDINALITY`, `MISSING_REQUIRED_CONSTRAINT`, `NAMING_AMBIGUOUS`, `DOMAIN_MISMATCH`, `OTHER_EXPLAINED`.

## Rating record schema

```csv
artifact_id,rater_id,presentation_order,rubric_version,d1_3nf,d2_naming,d3_constraints,d4_relationships,d5_domain,reason_codes,comment_redacted,rated_at_utc,missing_reason
```

## Adjudication and analysis

Do not replace independent ratings with consensus scores. Primary reliability is ordinal Krippendorff alpha with bootstrap CI; exact/adjacent agreement and pairwise weighted kappa are diagnostics. If alpha is below the preregistered threshold, retain data and report limitations; do not repeatedly rewrite the rubric after seeing conditions. Structural semantic mappings use a separate two-reviewer/third-adjudicator process and are not inferred from these ratings.

## Package manifest

Every pack contains rubric, instructions, calibration example, artifact files, rating CSV, manifest with SHA-256, random-order file and a private condition mapping held by the coordinator. Record generation timestamp and software/rubric versions.
