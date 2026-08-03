# Research Notes

## 1. Research Questions

### Main Question

**How can an LLM-based system with an interactive visual interface enable non-experts to create normalized and populated databases from text descriptions and heterogeneous documents, and how does it compare to a fully manual approach?**

### Research Questions (RQ0–RQ4)

**RQ0 (Overarching):** How can an LLM-based system with an interactive visual interface enable non-experts to create normalised and populated databases from text descriptions and heterogeneous documents, and how does it compare with a fully manual process?

*Type:* Controlled comparative evaluation.
*Evidence:* A three-arm experiment compares Manual, AI-Only, and AI + Interface conditions. The working prototype demonstrates feasibility but is not, by itself, evidence of superiority over a manual process.

**RQ1 (Schema Quality):** How does the quality of LLM-generated schemas compare to manually created gold-standard schemas, as judged by database experts?

*Type:* Quantitative evaluation (expert review).
*Hypothesis:* LLM-generated schemas will achieve expert quality ratings comparable to gold standards for simple and medium-complexity domains, but will degrade for complex domains with implicit relationships.
*Metrics:* 5-point Likert ratings across 5 dimensions (see Benchmark Protocol), Krippendorff's alpha with ordinal distance for inter-rater agreement.

**RQ2 (Population Accuracy):** How accurate is LLM-driven automatic data population at the cell level, measured against ground-truth data?

*Type:* Quantitative evaluation (automated metrics).
*Hypothesis:* Population accuracy will be high (>90% precision) for tabular source documents (CSV, Excel) and lower for unstructured text (PDF, TXT).
*Metrics:* Cell-level precision, recall, F1, normalisation checks, duplicate rate, error typology classification.

**RQ3 (Human-in-the-Loop Impact):** Does providing a visual review-and-edit interface for AI-generated schemas improve schema quality compared to an automatic-only approach?

*Type:* Between-subjects controlled experiment.
*Hypothesis:* Participants using the AI + Interface condition will produce schemas with higher expert quality ratings than participants using the AI-Only condition.
*Independent variable:* Assistance mode (Manual vs. AI-Only vs. AI + Interface). The preregistered RQ3 contrast is AI-Only vs. AI + Interface; the RQ0 contrast is Manual vs. AI + Interface.
*Dependent variables:* Schema quality (expert-rated), cognitive load (NASA-TLX), usability (SUS), task completion time.

**RQ4 (Interaction Patterns):** What interaction patterns emerge when non-expert users design databases via an LLM-powered visual interface?

*Type:* Qualitative / descriptive (interaction log analysis).
*Data:* All user actions logged: column renames, constraint toggles, table additions/removals, chat messages, query attempts, population triggers.
*Analysis:* Behavioural pattern coding, transition matrices between tool states, common error patterns.

---

## 2. Experimental Design

### Design Type

Three-arm, between-subjects, randomised controlled experiment. The AI + Interface arm is shared by the RQ0 and RQ3 preregistered contrasts.

### Groups

| Group | Condition | Schema Generation | Population | Role of Participant |
|---|---|---|---|---|
| M | Manual | Participant-created without generative AI | Participant maps/inserts data manually | Active creator |
| A | AI-Only | Fully automatic | Fully automatic | Reviewer only (no edits) |
| B | AI + Interface | AI-generated, user can edit via UI | Hybrid automatic | Active editor |

The Manual condition uses the same task brief, source documents, time limit, and output format. Participants may use a conventional visual relational-database tool and its documentation, but no generative AI, schema generator, or pre-built template. Tool, version, and any help opened are recorded.

### Datasets

Three datasets of increasing complexity (see Benchmark Protocol for details):

1. **Simple** — 3 tables, 2 relationships (e.g., Students + Courses + Enrollments)
2. **Medium** — 5 tables, 4 relationships (e.g., Library with Members, Books, Loans, Fines, Categories)
3. **Complex** — 8+ tables, 7+ relationships (e.g., Hospital with Patients, Doctors, Appointments, Treatments, Wards, Medications, Prescriptions, Invoices)

Each dataset includes:
- A set of source documents (PDF description + CSV data files)
- A gold-standard schema and populated database created by the research team
- Ground-truth cell-level data for population accuracy measurement

### Participants

- **Confirmatory target:** at least 34 completed participants per arm (102 total) for the two preregistered pairwise contrasts when planning for d = 0.7, α = 0.05, and power = 0.80; recruit approximately 114 to allow 10% attrition
- **Pilot:** 5–8 separate participants, excluded from confirmatory analyses
- **Recruitment:** University mailing lists, academic social media, professional networks
- **Inclusion criteria:** Self-identified non-experts in database design (no formal database coursework); comfortable with basic file operations
- **Exclusion criteria:** Professional database administrators, computer science faculty, prior exposure to the tool
- **Compensation:** Gift voucher or participation credit

### Procedure

1. **Pre-questionnaire:** Demographics, self-rated computer literacy, prior database experience
2. **Training (10 min):** Brief video tutorial showing the interface and basic operations
3. **Task (45 min):** Create a database from the provided documents using the assigned condition
4. **Post-questionnaires:** Raw NASA-TLX (six 0–100 ratings, aggregate = arithmetic mean) [7], SUS (10 standard items, 1–5; score 0–100) [8], free-text feedback
5. **Debrief:** Explanation of research goals, opportunity to withdraw data

### Power Analysis

For each preregistered two-group contrast, α = 0.05, power = 0.80, and expected d = 0.7 require approximately 34 completed participants per arm. Because the design has three arms, the confirmatory target is 102 completers, increased to approximately 114 recruits for attrition. If recruitment cannot support this target, the study is explicitly labelled exploratory; the sample target must not be lowered after looking at outcomes. The pilot is used to validate procedure and estimate variance, not to test hypotheses.

---

## 3. Rationale for LLM-Based Schema Generation

### Why Not Rule-Based Approaches?

Rule-based schema generation (e.g., classic functional-dependency discovery such as TANE) relies on [1,2]:

- **Functional dependency discovery** from tabular data — requires clean, complete, denormalised tables. Cannot handle PDF descriptions or natural language requirements.
- **Predefined mapping rules** — brittle across domains; a rule set for bibliographic databases does not generalise to inventory management.
- **No natural language understanding** — cannot interpret "I need to track which products each supplier provides, and a product can come from multiple suppliers".

*Note: an earlier draft cited "Heidari et al., 2021; the DTMINER family". This reference could not be positively verified and has been replaced by the canonical TANE algorithm (Huhtala et al., 1999) [1,2]. Verify the intended source before restoring it.*

LLMs, by contrast, bring broad world knowledge and have been trained on millions of database schemas, SQL queries, and documentation examples. They can:

- Infer implicit entities (e.g., understanding that "course enrollment" implies a many-to-many relationship requiring a junction table).
- Map colloquial domain vocabulary to database conventions (e.g., "ID number" → `INTEGER PRIMARY KEY`, "price" → `REAL NOT NULL`).
- Reason about functional dependencies from context even when no tabular data is present.

Recent work confirms that LLMs can perform schema matching and structured-data wrangling that classical matchers cannot [3,4], directly supporting the feasibility of an LLM-first schema-generation approach (see also [5,6]).

LLMs, by contrast, bring broad world knowledge and have been trained on millions of database schemas, SQL queries, and documentation examples. They can:

- Infer implicit entities (e.g., understanding that "course enrollment" implies a many-to-many relationship requiring a junction table).
- Map colloquial domain vocabulary to database conventions (e.g., "ID number" → `INTEGER PRIMARY KEY`, "price" → `REAL NOT NULL`).
- Reason about functional dependencies from context even when no tabular data is present.

### Why Human-in-the-Loop?

LLMs are not reliable enough for fully autonomous schema generation. Common failure modes include:

- **Hallucinated tables** — the LLM creates entities not mentioned in the source material.
- **Missing constraints** — foreign keys omitted, NOT NULL forgotten on mandatory columns.
- **Incorrect cardinality** — modelling a one-to-many as a many-to-many or vice versa.
- **Naming inconsistencies** — inconsistent use of singular/plural, different names for the same concept across runs.

The human-in-the-loop design allows domain experts to correct these errors using their own domain knowledge, while the LLM handles the mechanical aspects of normalisation and SQL generation.

---

## 4. Limitations

### 4.1 Current Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| **Single LLM provider per session** | Cannot compare provider quality within the same task | Store provider info in interaction logs for post-hoc analysis |
| **SQLite only** | No PostgreSQL/MySQL target databases | Export feature generates multi-dialect scripts |
| **No real user testing yet** | All current evaluation is by the research team | Planned experiments in Phases 3–6 |
| **PDF parsing limited to text** | Scanned documents, images, complex layouts yield empty content | Instruct users to provide TXT/CSV as primary source |
| **No column removal in migration** | Mistakes in schema design cannot be fully undone | Backup/restore provides full rollback |
| **Single-user only** | No multi-user collaboration, no user accounts | Acceptable for research; would need redesign for production |
| **No streaming export** | Very large exports (>100MB) held in memory | Acceptable for research-scale data (<10MB typical) |
| **Celery required for async tasks** | Without Redis, schema generation blocks HTTP request | Sync endpoints work without Celery |

### 4.2 Design Limitations

- **Prompt sensitivity** — Schema quality varies significantly with prompt wording. The fixed prompts in `app/core/llm.py` are the result of iterative refinement but may not be optimal for all domains.
- **Temperature setting** — Schema generation uses temperature 0.1 for reproducibility; population uses 0.0. These values were chosen heuristically.
- **Document truncation** — LLM-bound content is limited to 5,000 characters per document, with an additional combined-prompt limit. Runs record a categorised warning when unstructured input is truncated; evaluations must treat potentially omitted information as a system limitation.
- **Language** — The UI and prompts are in English and Italian mixed. The prompts are in English; the UI labels are Italian. This may affect non-Italian-speaking experiment participants.

---

## 5. Planned Experiments

### Experiment 1: Schema Quality Evaluation (RQ1)

- **Method:** Expert review of 30 generated schemas (3 datasets × 2 conditions × 5 runs each).
- **Reviewers:** 3 database experts (PhD-level or industry DBA with 5+ years).
- **Materials:** Anonymised schema printouts with table definitions, columns, constraints, and relationships.
- **Protocol:** Each reviewer rates each schema independently. Inter-rater agreement is measured using Krippendorff's alpha with ordinal distance. Scores are summarised across reviewers only after agreement analysis.

### Experiment 2: Population Accuracy Measurement (RQ2)

- **Method:** Automated cell-level comparison of 30 populated databases against ground-truth databases.
- **Script:** Python script comparing every cell in every table, classifying each as exact match, type-consistent match, null-in-source, wrong value, or missing.
- **Metrics:** Per-table and overall precision, recall, F1.

### Experiment 3: Between-Subjects User Experiment (RQ3)

- **Method:** Three-arm controlled lab or remote study with at least 102 completed participants, preceded by a separate 5–8 participant formative pilot.
- **Procedure:** As described in Section 2.
- **Analysis:** Independent-samples t-test (or Mann-Whitney U if assumptions violated) for schema quality scores, NASA-TLX, SUS.

### Experiment 4: Interaction Log Analysis (RQ4)

- **Method:** Sequence analysis of logged events from Experiment 3.
- **Techniques:** Markov transition matrices, clustering of user behavioural profiles, frequency analysis of edit types.

### Timeline (see Thesis Roadmap for details)

| Experiment | Planned Start | Duration | Status |
|---|---|---|---|---|
| Schema quality (RQ1) | Month 4 | 6 weeks | Planned |
| Population accuracy (RQ2) | Month 5 | 4 weeks | Planned |
| User experiment (RQ3) | Month 7 | 8 weeks | Planned |
| Interaction analysis (RQ4) | Month 9 | 6 weeks | Planned |

---

## 6. References

[1] Y. Huhtala, J. Kärkkäinen, P. Porkka, and H. Toivonen. "TANE: An Efficient Algorithm for Discovering Functional and Approximate Dependencies." *The Computer Journal*, 42(2):100–111, 1999. DOI: 10.1093/comjnl/42.2.100.

[2] T. Papenbrock et al. "Functional Dependency Discovery: An Experimental Evaluation of Seven Algorithms." *Proceedings of the VLDB Endowment (PVLDB)*, 8(10):1082–1093, 2015.

[3] Y. Zhang et al. "Schema Matching using Large Language Models." arXiv:2310.11779, 2023.

[4] A. Narayan, A. Floratou, F. Psallidas, et al. "Can Foundation Models Wrangle Your Data?" *Proceedings of the VLDB Endowment*, 16(4):782–795, 2022.

[5] S. Chaudhuri, N. Chhetri, and A. Neupane. "NL2Schema: Generating Database Schemas from Natural Language Descriptions." arXiv:2310.05978, 2023.

[6] E. Rahm and P. A. Bernstein. "A Survey of Approaches to Automatic Schema Matching." *The VLDB Journal*, 10(4):334–350, 2001.

[7] S. G. Hart and L. E. Staveland. "Development of NASA-TLX (Task Load Index)." *Human Mental Workload*, pages 139–183, 1988.

[8] J. Brooke. "SUS: A Quick and Dirty Usability Scale." *Usability Evaluation in Industry*, pages 189–194, 1996.

*(References [7–8] support the workload and usability measures used in RQ3 and the pilot.)*
