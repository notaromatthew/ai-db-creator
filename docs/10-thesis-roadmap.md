# Thesis Roadmap

## Overview

This document outlines the planned phases for the PhD research project "AI-DB-Creator: An LLM-Powered Visual Interface for Automatic Database Schema Generation and Population." The project is organised into seven phases spanning approximately 12 months. Phases 1–2 are complete; Phases 3–7 are planned.

---

## Phase 1: System Development and Architecture Definition (Complete)

**Timeline:** Months 1–3 (completed)

### Objectives
- Develop the core AI-DB-Creator application (backend + frontend)
- Define the system architecture and component boundaries
- Implement all 7 epistemic agents (Document Ingestion, Schema Generation, Database Creation, Data Population, Validation, Export, Backup)
- Establish the multi-provider LLM abstraction layer
- Implement the visual CRUD interface, NL-to-SQL querying, and multi-dialect export

### Deliverables
- Working backend (FastAPI + SQLAlchemy + LangChain) with all API endpoints
- Working frontend (React + TypeScript + TailwindCSS) with Dashboard, Project Page, Schema Viewer, Data Viewer, Query Builder
- Docker Compose deployment configuration
- Integration with OpenAI, Google Gemini, Groq, OpenRouter, and Ollama providers
- Backup/restore subsystem with automatic pre-destructive-operation snapshots

### Validation
- End-to-end manual testing with 3 benchmark datasets
- Schema generation produces valid 3NF structures for simple and medium datasets
- Population correctly inserts data from CSV and Excel sources

---

## Phase 2: Documentation, Paper Writing, Dataset Preparation (Current)

**Timeline:** Months 4–5 (current)

### Objectives
- Write all project documentation (this documentation suite)
- Prepare benchmark datasets with gold-standard schemas
- Develop automated evaluation scripts for population accuracy
- Record the user-reported institutional determination that prior ethics approval is not required for the current study
- Write the system description paper for conference submission

### Deliverables
- Documentation suite (11 documents covering project overview, technical manual, user manual, deployment guide, research notes, API map, thesis roadmap, benchmark protocol, risk register, data governance)
- Three benchmark datasets (simple, medium, complex) each with:
  - Source documents (CSV data files + PDF/TXT description)
  - Gold-standard NormalizedSchema (validated by domain experts)
  - Ground-truth databases with known cell values
- Automated evaluation pipeline for cell-level accuracy comparison
- Protocol amendment documenting the institutional determination and participant safeguards
- Draft of system paper targeting VLDB, SIGMOD, or ICDE demo track

### Risks
- Dataset complexity level calibration (too simple → ceiling effect; too complex → floor effect)
- Missing written trace of the institutional determination; archive the communication if available

---

## Phase 3: Evaluation of Generated Schemas (RQ1) (Observed student-rater panel)

**Timeline:** Months 6–7 (8 weeks)

### Objectives and observed status
- The planned sample was 3 database experts (PhD-level or industry DBA with 5+ years); the observed export contains 45 computer-science students aged 17--18 who were studying databases. They are reported as trained student raters, not database experts.
- The observed package contains 30 schemas: 3 datasets × 2 recorded benchmark conditions (`baseline` and `full_llm`) × 5 runs. These conditions must not be relabelled as the RQ3 participant arms.
- All 45 evaluators rated every schema on 5 dimensions (3NF compliance, naming quality, constraint coverage, relationship accuracy, domain alignment) using a 5-point Likert scale.
- Measure inter-rater agreement with Krippendorff's alpha using ordinal distance
- Compare mean quality scores across conditions

### Methods
- Blind review: schemas are anonymised and presented in random order
- Independence is claimed only if the administration records show individual, condition-blind ratings without discussion or access to peers' scores
- Analysis: mean ± SD per dimension, ordinal Krippendorff's alpha for agreement, independent-samples t-test or Mann-Whitney U

### Planned success criteria
- Krippendorff's alpha ≥ 0.67 for tentative conclusions and ≥ 0.80 for confirmatory interpretation
- AI + Interface condition scores significantly higher (p < 0.05) than AI-Only on at least 3 of 5 dimensions
- Effect size d ≥ 0.5 for the primary dimension (3NF compliance)

Observed analyses and provenance are stored in `backend/reports/rq1_analysis/`. The difference between the planned and observed evaluator sample is a protocol deviation, not a retrospective redesign. Institutional verification of the curriculum, independence procedure, and assent/consent arrangements for minors remains separate from the statistical analysis.

---

## Phase 4: Automated Population Accuracy Measurement (RQ2) (Completed, exploratory)

**Timeline:** Month 7–8 (4 weeks overlap with Phase 3)

### Objectives
- Measure cell-level accuracy on facts observable in the supplied documents
- Compare accuracy across dataset complexity levels
- Compare accuracy across source document types only after deriving semantically equivalent CSV/XLSX/PDF/TXT variants from one canonical observable fact set
- Classify errors by typology (see Benchmark Protocol)

### Methods
- Automated Python script reads the declared observable scope from each dataset's `evaluation_spec.json`
- Compares observable cells to the corresponding ground-truth cells and retains the full gold only as sensitivity analysis
- Matching is performed at two levels:
  - **Exact match:** string equality after type-appropriate normalisation
  - **Type-consistent match:** same value after type coercion (e.g., 1.0 ≡ 1, "true" ≡ True)
- All mismatches are classified by error type
- Frozen functional queries test information preservation independently of synthetic identifiers and schema decomposition

The audit in `docs/20-rq2-functional-equivalence-protocol.md` records that the
current bundles contain no XLSX variants and that several gold rows or columns
are not present in any source document. Historical full-gold F1 must not be
presented as primary extraction accuracy.

The consensus-amended `rq2_functional_v2` matrix is complete: 30/30 runs,
five per dataset-condition cell, all with LLM population and no fallback. The
current results, integrity checks and limitations are reported in
`docs/21-rq2-primary-results.md`. The format-isolated experiment is also
complete as a separate exploratory analysis (38/40 primary runs, plus a
clearly separated 40/40 post-recovery sensitivity).

### Success Criteria
- Overall cell-level F1 ≥ 0.85 on CSV/Excel sources
- Overall cell-level F1 ≥ 0.60 on PDF/TXT sources
- Duplicate rate < 5% across all tables
- Precision ≥ recall for all datasets (no systematic over-insertion)

---

## Phase 5: Between-Subjects User Experiment (RQ3) (Planned)

**Timeline:** Months 8–10 (8 weeks)

### Objectives
- Run a formative pilot with 5–8 non-experts; exclude pilot data from confirmatory analyses
- Recruit approximately 114 participants to obtain at least 34 completed cases in each of three arms after attrition
- Randomly assign to Manual, AI-Only, or AI + Interface; preregister Manual vs. AI + Interface for RQ0 and AI-Only vs. AI + Interface for RQ3
- Each participant creates a database from one of the three datasets
- Collect: schema quality (expert-rated post-hoc), residual error rate, completion time, and task success rate

### Procedure
1. **Pre-session (online, 5 min):** Informed consent and short demographic form
2. **Training video (10 min):** Pre-recorded walkthrough of the system
3. **Task (45 min):** Participants create a database from assigned dataset in their assigned condition
4. **Post-task (5 min):** optional privacy-filtered free-text debrief; no NASA-TLX or SUS in the current protocol
5. **Debrief:** Explanation of purpose, opportunity to withdraw

### Analysis Plan
- **Primary analyses:** Two preregistered pairwise contrasts: Manual vs. AI + Interface (RQ0), and AI-Only vs. AI + Interface (RQ3), with multiplicity control and effect sizes with 95% confidence intervals
- **Secondary analysis:** completion time and task-success summaries; no perceived-load or usability questionnaire outcome
- **Exploratory analysis:** Correlation between computer literacy and schema quality within each group
- **Power:** α = 0.05, power = 0.80, expected d = 0.7 → approximately 34 completed participants per arm (102 total); recruit approximately 114 for 10% attrition. A smaller achieved sample is reported as exploratory rather than retrospectively redefining the target.

### Materials Needed
- Pre-session: online consent and demographic form
- Training: screen-capture video with narration
- Task: prepared project in AI-DB-Creator with uploaded documents (one of three datasets)
- Post-task: short debrief and withdrawal reminder; questionnaire forms are excluded from the current study
- Debrief: information sheet with research team contact details
- Pilot protocol and frozen issue log: `docs/14-usability-pilot-protocol.md`
- Manual-condition tool, tutorial and deviation protocol: `docs/16-manual-condition-protocol.md`

---

## Phase 6: Interaction Log Analysis (RQ4) (Planned)

**Timeline:** Months 10–11 (6 weeks)

### Objectives
- Analyse interaction logs collected during the Phase 5 experiment
- Identify common user behaviour patterns
- Characterise differences between successful and unsuccessful schema designs
- Quantify the impact of specific interface features (chat, edit mode, constraints)

### Methods
- **Sequence analysis:** Convert logged events into ordered sequences per participant, compute transition matrices between tool states (view schema, edit schema, chat, populate, explore data)
- **Cluster analysis:** Group participants by behavioural profile (e.g., "chat-heavy", "edit-heavy", "minimal interaction")
- **Outcome correlation:** Correlate behavioural clusters with schema quality and residual-error outcomes
- **Error analysis:** Identify common patterns of schema errors (e.g., "removing foreign keys", "adding unnecessary tables")

The frozen analysis entry point is `backend/analyze_user_study.py`. It consumes the three pseudonymous exports documented in `docs/19-user-study-analysis.md`, applies the preregistered RQ0/RQ3 contrasts, and keeps RQ4 analyses explicitly exploratory.

### Tools
- Python + pandas for event extraction and preprocessing
- Python `transitions` library or custom Markov chain implementation
- scikit-learn for clustering (K-means, DBSCAN)
- Matplotlib / Seaborn for visualisation of transition matrices and cluster profiles

---

## Phase 7: Paper Submission and Thesis Writing (Planned)

**Timeline:** Months 11–14 (12 weeks)

### Objectives

#### Paper Submissions
1. **System demonstration paper** (4 pages) to VLDB 2027 demo track or ICDE 2027 demo track
   - Title: "AI-DB-Creator: LLM-Powered Database Design for Non-Experts"
   - Content: System architecture, walkthrough scenario, screencast
2. **Full research paper** (12 pages) to SIGMOD 2028 or VLDB 2028
   - Title: "From Documents to Databases: LLM-Generated Schemas with Human-in-the-Loop Validation"
   - Content: Full experimental results for RQ1–RQ4, discussion, limitations

#### Thesis Writing
- **Chapter 1: Introduction** — Motivation, problem statement, research questions, contributions
- **Chapter 2: Related Work** — Automatic schema generation, NL-to-SQL, visual database design tools, LLM for data management
- **Chapter 3: System Design** — Architecture, multi-agent decomposition, implementation details
- **Chapter 4: Methodology** — Experimental design, datasets, participants, metrics
- **Chapter 5: Results** — RQ1 (expert evaluation), RQ2 (population accuracy), RQ3 (user experiment), RQ4 (interaction analysis)
- **Chapter 6: Discussion** — Interpretation of findings, limitations, threats to validity
- **Chapter 7: Conclusion** — Summary, contributions, future work

---

## Timeline Summary

| Phase | Description | Start | End | Duration |
|---|---|---|---|---|
| 1 | System Development | Month 1 | Month 3 | 3 months |
| 2 | Documentation & Datasets | Month 4 | Month 5 | 2 months |
| 3 | Expert Evaluation (RQ1) | Month 6 | Month 7 | 2 months |
| 4 | Population Accuracy (RQ2) | Month 7 | Month 8 | 1 month |
| 5 | User Experiment (RQ3) | Month 8 | Month 10 | 2 months |
| 6 | Interaction Analysis (RQ4) | Month 10 | Month 11 | 1.5 months |
| 7 | Writing & Submission | Month 11 | Month 14 | 3 months |

**Total:** 14 months from project start.

### Visual Timeline

```
Month:   1  2  3  4  5  6  7  8  9  10  11  12  13  14
Phase 1  ████████████████
Phase 2           ████████████
Phase 3                    ████████████
Phase 4                         ████████
Phase 5                              ████████████
Phase 6                                        ██████
Phase 7                                              ████████████
```

---

## Contingency Planning

| Risk | Contingency | Impact on Timeline |
|---|---|---|
| Low expert recruitment | Use 2 experts instead of 3; report agreement metrics with fewer raters | +0 weeks (reduced statistical power) |
| Low participant recruitment | Extend recruitment period; use snowball sampling; offer higher compensation | +2–4 weeks |
| LLM provider API change | Switch to alternative provider (system is provider-agnostic) | +1 week (testing) |
| Institutional determination not archived | Preserve the communication if available and report its status without inferring formal approval | Documentation risk |
| Null results in RQ3 | Report negative finding; focus discussion on why AI-Only may be sufficient for simple datasets | +0 weeks (no extra work) |
| Major bug in experiment | Pilot test with 5 colleagues before each participant session | Prevents delays |
