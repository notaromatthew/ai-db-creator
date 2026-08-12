# Pilot Issue Log and Research Freeze — DRAFT / UNAPPROVED

> Operational template. Pilot data are formative and excluded from confirmatory analyses. Passing this checklist does not imply ethics approval.

## Pilot issue log schema

```csv
issue_id,opened_at_utc,pilot_session,arm,dataset,category,severity,evidence_without_pii,participant_impact,comparability_impact,temporary_action,owner,resolution,verification_test,verified_by,closed_at_utc,requires_protocol_amendment,approval_status
```

Severity: `S1` safety/privacy/data-loss; `S2` task-blocking or condition contamination; `S3` outcome-affecting but recoverable; `S4` cosmetic. Categories: consent/privacy, allocation, tutorial, usability, accessibility, upload/parser, LLM/provider, schema, population, export, logging, questionnaire, facilitator, infrastructure.

## Pilot exit criteria

- The hospital `treatments` and `prescriptions` natural/entity keys pass the
  uniqueness validator after manifest or gold-data correction; the current
  draft failure is a research-freeze blocker.
- No open S1/S2 issue; every S3 has a documented disposition.
- All three arms complete the full flow on every study dataset in a clean environment.
- Assigned capabilities are technically enforced; no cross-arm leakage.
- Valid exports and hashes are produced; timers and completion status agree.
- Event loss and duplicate-event rates are below frozen thresholds `[specify]`.
- Questionnaire scoring and missing-item behavior are verified.
- Participant wording, tutorial duration and facilitator interventions are reviewed for equivalence.
- Accessibility checks cover keyboard operation, focus, readable errors and zoom.
- Withdrawal/deletion and incident-response drills are completed by authorised staff.

## Freeze checklist

Record version and SHA-256 for: release/commit, deployment image, dependency locks, provider/model and exposed parameters, prompt templates, datasets/source files/gold schemas, canonical alignment manifests, evaluator, functional workloads/expected results, arm configurations, tutorials/task brief, consent/privacy/debrief, questionnaires/scoring, allocation procedure/seed custody, expert rubric/package, event taxonomy, SAP/preregistration and export scripts.

Record infrastructure region, clock source, browser/OS/hardware, rate limits, feature flags, logging schema, backup/recovery and monitoring thresholds. Produce a signed freeze manifest with date, owner, reviewer and `UNAPPROVED`, `APPROVED FOR PILOT` or `APPROVED FOR CONFIRMATORY USE`; only authorised humans may change approval status.

## Change control after freeze

Classify changes as cosmetic, non-material operational, or material to intervention/outcome/comparability. Material changes create a protocol version and require the applicable ethics/governance decision before further collection. Never pool versions silently. Preserve old artifacts and record whether outcomes were inspected before the change.
