# 09 - Usability Pilot Protocol & Experimental Results

> **DRAFT / UNAPPROVED — ETHICS REVIEW PENDING.** No controlled participant study or expert panel is represented here as completed. Any benchmark values in older versions of this page are not validated evidence. Development outputs in `docs/18-results-draft.md` are legacy exploratory and must be regenerated under the frozen protocol.

> **Source Documents**: `docs/10-thesis-roadmap.md`, `docs/14-usability-pilot-protocol.md`, `docs/18-results-draft.md`

---

## 1. Usability Pilot Study Protocol

The proposed pilot would evaluate user cognitive load and platform usability (RQ0/RQ3) after ethics approval and research freeze. The target population, recruitment channels and eligibility criteria remain subject to approval.

### Evaluation Instruments:
1. **NASA-TLX (Task Load Index)**:
   - Measures 6 sub-scales: Mental Demand, Physical Demand, Temporal Demand, Performance, Effort, and Frustration.
   - Submitted via `POST /api/surveys/nasa-tlx`.
2. **SUS (System Usability Scale)**:
   - 10-item questionnaire yielding a composite usability score (0 to 100).
   - Submitted via `POST /api/surveys/sus`. Target benchmark score: **> 75.0** (Above Average usability).

---

## 2. Legacy Development Results (`docs/18-results-draft.md`)

The existing temperature 0.1/0.5 benchmark reports were generated during evaluator development. They are useful for debugging variance and evaluator limitations but are non-confirmatory, cannot be pooled with future evaluator versions and do not establish provider rankings. Confirmatory tables remain intentionally empty until model/temperature, datasets, evaluator, alignment and analysis are frozen.

---

## 3. PhD Thesis Roadmap & Milestones

1. **Engineering baseline:** implemented and subject to continuing verification.
2. **Methodology and evaluator revision:** in progress.
3. **Ethics/privacy review and pilot readiness:** pending; no recruitment authorised by these documents.
4. **Formative pilot, research freeze and confirmatory collection:** future gates.
5. **Analysis and publication:** only after data lock and reproducibility review.
