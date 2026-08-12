# Paper Skeleton and Reproducibility Checklist — DRAFT / UNAPPROVED

> Writing scaffold only. It contains no claim of ethical approval, completed recruitment, validated results or generalisability.

## Paper skeleton

1. **Title and abstract:** problem, three-arm design, datasets, primary outcomes, effect estimates with uncertainty; no unsupported “first” or “state-of-the-art” claim.
2. **Introduction:** non-expert database-design problem; RQ0–RQ4; contributions separated into system, benchmark and human evidence.
3. **Related work:** text-to-schema/data integration, LLM database tools, mixed-initiative interfaces, human factors and evaluation methodology.
4. **System:** architecture, model/provider boundary, chat-to-accept flow, validation interface, population/provenance, security assumptions.
5. **Methods:** preregistration/version, datasets/gold construction, canonical facts, structural and functional equivalence, three arms, allocation, participants, expert blinding, outcomes, event taxonomy, SAP, ethics/privacy status.
6. **Results:** participant/run flow; RQ1 reliability and quality; RQ2 facts/failures/workload; RQ0/RQ3 contrasts; RQ4 associations; sensitivity analyses. Label existing evaluator-v1/temperature results exploratory.
7. **Discussion:** practical meaning, stochasticity, human validation, discordance between physical fidelity and functional equivalence.
8. **Threats:** construct validity, alignment adjudication, provider drift, dataset/domain scope, learning/tool fairness, missingness, multiplicity, LLM-as-judge bias.
9. **Ethics and data governance:** use only final approved wording and reference; do not imply approval while pending.
10. **Limitations/conclusion:** calibrated claims and negative findings.

## Artifact checklist

- [ ] immutable repository release/commit and licence
- [ ] environment/container and dependency locks
- [ ] source datasets with licences, hashes and data statement
- [ ] gold schemas/databases and construction/adjudication record
- [ ] prompt templates, provider/model/parameters and drift limitation
- [ ] evaluator, canonical alignment manifests and unit tests
- [ ] functional workloads and expected-result hashes
- [ ] arm configurations, tutorials and task materials
- [ ] preregistration, SAP and amendments with timestamps
- [ ] consent/privacy/debrief versions, with approved status stated accurately
- [ ] pseudonymised data dictionary and disclosure-reviewed release
- [ ] attempted-run and participant flow, including failures/exclusions
- [ ] expert artifact order, rubric, ratings and agreement code
- [ ] event taxonomy, derivation code and analysis decisions
- [ ] one-command or documented reproduction path for every table/figure
- [ ] checksums, random seeds, software session info and compute/cost statement

## Claim-to-evidence matrix

For every abstract/conclusion claim record: claim ID, RQ, outcome/contrast, preregistered status, analysis/table/figure, estimate/CI, population/domain, sensitivity support and limitation. A claim without a populated evidence row is removed or labelled hypothesis.

## Results placeholders

Use `n/N`, effect estimate, 95% CI and adjusted p-value where applicable. Never write “no difference” solely from `p > .05`; report compatibility interval. Distinguish failed execution, missing artifact and low-quality output. Do not merge strict cell, canonical fact and functional workload scores into one undocumented accuracy number.
