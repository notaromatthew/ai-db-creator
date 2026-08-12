# Thesis Roadmap

> **PLANNING DRAFT / UNAPPROVED.** Phase labels and dates are planning statements, not evidence of ethics approval, completed recruitment or confirmatory results. The current operational gate is research/pilot readiness and artifact freeze.

## Overview

This document outlines a draft sequence for the PhD research project "AI-DB-Creator: An LLM-Powered Visual Interface for Automatic Database Schema Generation and Population." Phase labels are planning aids, not completion evidence; implementation and research-freeze status must be read from the readiness gates.

---

## Phase 1: System Development and Architecture Definition (Complete)

**Timeline:** Months 1–3 (planned baseline; completion not asserted here)

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
- Population paths exist for CSV and Excel sources; correctness remains an evaluation question

---

## Phase 2: Documentation, Paper Writing, Dataset Preparation (In progress; research freeze pending)

**Timeline:** Months 4–5 (current)

### Objectives
- Write all project documentation (this documentation suite)
- Prepare benchmark datasets with gold-standard schemas
- Develop automated evaluation scripts for population accuracy
- Prepare ethics approval application for human subjects research
- Write the system description paper for conference submission

### Deliverables
- Documentation suite (11 documents covering project overview, technical manual, user manual, deployment guide, research notes, API map, thesis roadmap, benchmark protocol, risk register, data governance)
- Three benchmark datasets (simple, medium, complex) each with:
  - Source documents (CSV data files + PDF/TXT description)
  - Gold-standard NormalizedSchema (validated by domain experts)
  - Ground-truth databases with known cell values
- Automated evaluation pipeline for cell-level accuracy comparison
- Ethics clearance application (IRB / university ethics committee)
- Draft of system paper targeting VLDB, SIGMOD, or ICDE demo track

### Risks
- Dataset complexity level calibration (too simple → ceiling effect; too complex → floor effect)
- Ethics approval delays (typically 4–8 weeks at most universities)

---

## Phase 3: Expert Evaluation of Generated Schemas (RQ1) (Planned)

**Timeline:** Months 6–7 (8 weeks)

### Objectives
- Recruit 3 database experts (PhD-level or industry DBA with 5+ years)
- Generate 30 schemas: 3 datasets × 2 conditions (AI-Only vs. AI + Interface) × 5 runs
- Experts rate each schema on 5 dimensions (3NF compliance, naming quality, constraint coverage, relationship accuracy, domain alignment) using a 5-point Likert scale
- Measure inter-rater agreement with Krippendorff's alpha using ordinal distance
- Compare mean quality scores across conditions

### Methods
- Blind review: schemas are anonymised and presented in random order
- Each expert works independently
- Analysis: mean ± SD per dimension, ordinal Krippendorff's alpha for agreement, independent-samples t-test or Mann-Whitney U

### Success Criteria
- Krippendorff's alpha ≥ 0.67 for tentative conclusions and ≥ 0.80 for confirmatory interpretation
- AI + Interface condition scores significantly higher (p < 0.05) than AI-Only on at least 3 of 5 dimensions
- Effect size d ≥ 0.5 for the primary dimension (3NF compliance)

---

## Phase 4: Automated Population Accuracy Measurement (RQ2) (Planned)

**Timeline:** Month 7–8 (4 weeks overlap with Phase 3)

### Objectives
- Measure cell-level accuracy of automatic data population for all 30 generated databases
- Compare accuracy across dataset complexity levels
- Compare accuracy across source document types (CSV vs. Excel vs. PDF vs. TXT)
- Classify errors by typology (see Benchmark Protocol)

### Methods
- Automated Python script reads every cell from every table in each generated database
- Compares each cell to the corresponding cell in the ground-truth database
- Matching is performed at two levels:
  - **Exact match:** string equality after type-appropriate normalisation
  - **Type-consistent match:** same value after type coercion (e.g., 1.0 ≡ 1, "true" ≡ True)
- All mismatches are classified by error type

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
- Determine recruitment only after the SAP, allocation design and power analysis are approved; existing numerical scenarios are planning inputs, not a final target
- Randomly assign to Manual, AI-Only, or AI + Interface; preregister Manual vs. AI + Interface for RQ0 and AI-Only vs. AI + Interface for RQ3
- Each participant creates a database from one of the three datasets
- Collect: schema quality (expert-rated post-hoc), NASA-TLX, SUS, completion time, task success rate

### Procedure
1. **Pre-session (online, 5 min):** Informed consent, demographics questionnaire
2. **Training video (10 min):** Pre-recorded walkthrough of the system
3. **Task (45 min):** Participants create a database from assigned dataset in their assigned condition
4. **Post-task (10 min):** Raw NASA-TLX (six 0–100 ratings; aggregate mean), SUS (10 standard 1–5 items; score 0–100), free-text feedback
5. **Debrief:** Explanation of purpose, opportunity to withdraw

### Analysis Plan
- **Primary analyses:** Two preregistered pairwise contrasts: Manual vs. AI + Interface (RQ0), and AI-Only vs. AI + Interface (RQ3), with multiplicity control and effect sizes with 95% confidence intervals
- **Secondary analysis:** Mann-Whitney U for NASA-TLX and SUS scores (non-normal distributions anticipated)
- **Exploratory analysis:** Correlation between computer literacy and schema quality within each group
- **Power:** effect-size, attrition and sample-size assumptions remain draft scenarios. A locked SAP and approved power analysis must define the final target before recruitment.

### Materials Needed
- Pre-session: online consent form + questionnaire
- Training: screen-capture video with narration
- Task: prepared project in AI-DB-Creator with uploaded documents (one of three datasets)
- Post-task: NASA-TLX and SUS forms (built into the application)
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
- **Outcome correlation:** Correlate behavioural clusters with schema quality scores and NASA-TLX ratings
- **Error analysis:** Identify common patterns of schema errors (e.g., "removing foreign keys", "adding unnecessary tables")

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
| Ethics approval delay | Submit to alternative committee; start Phase 3 (expert eval, no human subjects) immediately | +0–8 weeks (can parallelise) |
| Null results in RQ3 | Report negative finding; focus discussion on why AI-Only may be sufficient for simple datasets | +0 weeks (no extra work) |
| Major bug in experiment | Pilot test with 5 colleagues before each participant session | Prevents delays |
