# Usability Pilot Protocol

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
5. Conduct a short debrief focused on confusing concepts and missing feedback; do not administer Raw NASA-TLX or SUS in the current protocol.

Do not record document contents, credentials, names, email addresses, IP addresses, or raw chat/query text in interaction logs. Screen/audio recording requires separate explicit consent and a documented retention period.

## Exit Criteria

The confirmatory study may start only when:

- no participant is blocked by a severity-high usability defect;
- all three conditions can produce the required output within the time limit;
- event logs contain run ID, condition, timestamps, before/after state hashes, model configuration where applicable, and task completion status;
- the participant flow reaches debrief and completion without presenting questionnaire screens;
- the tutorial and task brief are frozen and versioned.

## Change Control

Maintain a pilot issue log with severity, affected condition, evidence, resolution, and verification. Freeze the application version, prompt version, datasets and instructions after the exit review. Any later material change requires a documented amendment and a renewed check of institutional requirements.

The exclusion of the questionnaires and the reported institutional determination are documented in `docs/23-study-protocol-amendment-2026-11-18.md`.
