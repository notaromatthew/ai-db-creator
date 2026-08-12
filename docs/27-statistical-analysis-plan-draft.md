# Statistical Analysis Plan — DRAFT / UNAPPROVED

> Analysis draft to be frozen with the preregistration before confirmatory data inspection. It is not evidence that collection or ethical review is complete.

## Populations and data lock

Primary human population is intention-to-treat; per-protocol is sensitivity only. Benchmark population includes all attempted frozen runs, with successful-run quality conditional on success and failure rate separately. Analysts verify hashes, exclusions, blinded rating lock and a signed freeze manifest before unblinding. Produce a CONSORT-style participant flow and benchmark-run flow.

## Descriptive reporting

By arm/dataset report n, missingness, mean/SD, median/IQR, range and distribution plots as appropriate. Do not significance-test baseline balance. Report expert agreement before aggregating scores. Every percentage includes numerator/denominator.

## Primary human models

- RQ0 schema composite: linear model `quality ~ arm_contrast + dataset + experience_stratum`, heteroskedasticity-robust SE; Interface versus Manual primary. Ordinal mixed-model sensitivity uses individual dimension/rater observations with artifact and rater effects.
- RQ3 residual errors: negative-binomial regression with `arm`, dataset and experience; Interface versus AI-Only primary. If convergence/dispersion fails, use robust Poisson and nonparametric contrast sensitivity.

Holm-adjust the two primary human contrast p-values at family alpha .05. Report adjusted/unadjusted p, marginal mean difference or incidence-rate ratio, standardized effect and 95% CI. Do not switch the primary model based solely on Shapiro–Wilk or Levene p-values.

## RQ1

Ordinal Krippendorff alpha with bootstrap 95% CI per dimension and overall is primary agreement. D1 3NF is key schema outcome. Analyse ratings with an ordinal mixed model including condition and dataset, random intercepts for artifact and rater where identifiable. Relationship F1 and deterministic constraint coverage are separate secondary metrics. Apply Holm within the five dimensions.

## RQ2

Primary per-run metric is `canonical_fact_micro_f1`; also report TP, FP, FN, `|G|`, `|P|`, precision and recall. Model/contrast uses run-level outcomes with dataset fixed effects and condition; because F1 is bounded, use nonparametric stratified bootstrap CIs and a permutation/randomisation-compatible condition contrast where exchangeability holds. With few datasets, do not claim broad domain generalisation.

Strict physical-cell fidelity, macro-table scores, natural-key duplicate rate, source-type strata and `functional_workload_v1` metrics are secondary. Cluster/hierarchical bootstrap may resample dataset → run → entity for descriptive uncertainty; cell-level Wilson intervals are not used for F1 or stochastic-run means. Failed runs remain in success-rate denominators. Quality among successful runs is explicitly conditional.

## RQ3 secondary outcomes

Analyse Raw NASA-TLX, SUS and log completion time with the same covariates and robust intervals. Task completion uses logistic regression or exact risk differences if sparse. Questionnaire scoring follows original rules; no bespoke reverse coding. Mediation claims are not planned.

## RQ4

Within Interface arm, regress final improvement on the three preregistered event features, controlling baseline quality, dataset, experience and active time. Use robust SE and report standardized coefficients/partial associations. Apply BH-FDR to the preregistered RQ4 feature family. Remaining feature engineering, clustering, transitions and sequence mining are exploratory with bootstrap stability and full codebook disclosure.

## Missingness and sensitivity

Follow `docs/19-preregistration-draft.md`. Report complete-case and multiple-imputation sensitivity where MAR is plausible; imputation model includes assignment, dataset, experience, completion/process variables and observed outcomes without using post-withdrawal data. Pattern-mixture/bounds sensitivity addresses technical failures. No outcome-driven exclusion, winsorisation or outlier deletion; influential points are retained and sensitivity reported.

## Multiplicity and interpretation

Families: two human primary contrasts (Holm); five RQ1 dimensions (Holm); stated questionnaire outcomes (Holm); RQ4 features (BH-FDR). RQ2 primary is separately labelled. All other analyses are secondary/exploratory. Statistical significance is not functional importance; conclusions use effect sizes, uncertainty, failure rates and prespecified thresholds.

## Reproducible outputs

One locked script creates analysis tables/figures from an immutable package. Record software/session info, random seeds, package lock, input/output hashes and warnings. Generate a machine-readable decision log for deviations and a results table that distinguishes preregistered, secondary and exploratory analyses.

## Implemented locked candidate (unapproved)

`backend/research_configs/sap-locked-candidate-v1.json` and
`backend/research_configs/analysis-input-v1.schema.json` are a versioned,
machine-readable implementation candidate for this draft. The offline command
`python locked_candidate_analysis.py --input <package.json> --output <directory>`
validates controlled values and units, keeps failed benchmark attempts in the
flow, emits deterministic hashed outputs, and records the RQ0, RQ3, RQ2 and RQ4
model/contrast commitments above. Until external protocol/SAP approval and a
verified freeze are supplied, inferential execution is disabled and every
output is labelled `locked_candidate_unapproved`; technical readiness does not
make it confirmatory evidence.
