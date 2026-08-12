# Usability Pilot Protocol

> **DRAFT / UNAPPROVED — ETHICS REVIEW PENDING.** This template does not authorise recruitment or data collection. Pilot observations are formative and must be excluded from confirmatory analyses.

## Purpose

Run a formative pilot before the confirmatory RQ0/RQ3 experiment to identify usability failures, unclear terminology, logging gaps, and task instructions that unintentionally favour one condition. Pilot participants are not included in the confirmatory dataset.

## Sample

- Recruit 5–8 people who meet the final non-expert inclusion criteria.
- Include a mix of technical confidence, age, and prior spreadsheet experience.
- Assign at least one participant to each of Manual, AI-Only, and AI + Interface; use the remaining participants on the condition with the greatest procedural uncertainty.

## Session

1. Obtain pilot consent and assign a pseudonymous participant ID.
2. Deliver the same tutorial planned for the final condition.
3. Ask the participant to think aloud while completing the task.
4. Record task completion, time per workflow phase, errors, requests for help, abandoned actions, and misunderstood labels.
5. Administer Raw NASA-TLX and SUS only after task completion.
6. Conduct a 10-minute debrief focused on confusing concepts and missing feedback.

Do not record document contents, credentials, names, email addresses, IP addresses, or raw chat/query text in interaction logs. Screen/audio recording requires separate explicit consent and a documented retention period.

## Exit Criteria

The confirmatory study may start only when:

- no participant is blocked by a severity-high usability defect;
- all three conditions can produce the required output within the time limit;
- event logs contain run ID, condition, timestamps, before/after state hashes, model configuration where applicable, and task completion status;
- Raw NASA-TLX and SUS reject incomplete or out-of-range responses;
- the tutorial and task brief are frozen and versioned.

## Change Control

Maintain a pilot issue log with severity, affected condition, evidence, resolution, and verification. Freeze the application version, prompt version, datasets, questionnaires, and instructions after the exit review. Any later material change requires a documented amendment and, when applicable, ethics approval.

## References

- S. G. Hart and L. E. Staveland. "Development of NASA-TLX (Task Load Index): Results of Empirical and Theoretical Research." *Human Mental Workload*, 1988.
- J. Brooke. "SUS: A Quick and Dirty Usability Scale." *Usability Evaluation in Industry*, 1996.

Both questionnaires are used in the pilot (Raw NASA-TLX and SUS, administered after task completion). Validation references for score interpretation follow the same sources used in the confirmatory protocol (`docs/11-benchmark-protocol.md`).
