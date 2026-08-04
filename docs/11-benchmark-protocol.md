# Benchmark Protocol for RQ1 and RQ2

## 1. Dataset Descriptions

Three datasets of increasing complexity are used to evaluate schema generation quality (RQ1) and population accuracy (RQ2). Each dataset includes:

- Source documents (CSV data files + PDF/TXT description)
- Gold-standard `NormalizedSchema` (tables, columns, constraints, relationships)
- Ground-truth SQLite database with known cell values

### 1.1 Dataset A: Simple — University Enrollment

| Aspect | Detail |
|---|---|
| **Domain** | University course enrollment system |
| **Number of tables** | 3 |
| **Tables** | `students`, `courses`, `enrollments` |
| **Relationships** | 2 (one-to-many: student → enrollments, course → enrollments) |
| **Source documents** | 1 PDF description (2 paragraphs), 1 CSV file (30 rows, 3 columns) |
| **Gold-standard tables** | 3 |
| **Gold-standard columns** | 10 total |
| **NOT NULL columns** | 6 |
| **Foreign keys** | 2 |
| **Complexity features** | Single junction table, no transitive dependencies, obvious PKs |

### 1.2 Dataset B: Medium — Library Management

| Aspect | Detail |
|---|---|
| **Domain** | Public library with members, books, loans, fines, categories |
| **Number of tables** | 5 |
| **Tables** | `members`, `books`, `categories`, `loans`, `fines` |
| **Relationships** | 4 (book → category, member → loans, book → loans, loan → fines) |
| **Source documents** | 1 PDF description (1 page), 2 CSV files (books: 50 rows, members: 20 rows) |
| **Gold-standard tables** | 5 |
| **Gold-standard columns** | 22 total |
| **NOT NULL columns** | 14 |
| **Foreign keys** | 4 |
| **Complexity features** | Implicit relationship (fine depends on loan which depends on member and book), date logic for overdue calculation |

### 1.3 Dataset C: Complex — Hospital Management

| Aspect | Detail |
|---|---|
| **Domain** | Private hospital with patients, doctors, appointments, treatments, wards, medications, prescriptions, invoices |
| **Number of tables** | 8 |
| **Tables** | `patients`, `doctors`, `wards`, `appointments`, `treatments`, `medications`, `prescriptions`, `invoices` |
| **Relationships** | 7+ (including many-to-many: treatments ↔ medications via prescriptions) |
| **Source documents** | 1 PDF description (3 pages), 2 CSV files (patients: 100 rows, appointments: 200 rows), 1 TXT file with operational notes |
| **Gold-standard tables** | 8 |
| **Gold-standard columns** | 42 total |
| **NOT NULL columns** | 28 |
| **Foreign keys** | 7 |
| **Complexity features** | Many-to-many with junction table, multi-column FKs, cyclic references (invoice references appointment which references patient), implicit entities (ward assignment inferred from doctor's department) |

---

## 2. Gold-Standard Schema Definitions

Each gold-standard schema is defined as a `NormalizedSchema` JSON object with:

- `tables`: list of `TableDef` objects (name, columns with name/data_type/is_primary_key/is_foreign_key/foreign_key_table/foreign_key_column/is_unique/is_not_null)
- `relationships`: list of `RelationshipDef` objects (type, from_table/from_column, to_table/to_column)

Gold standards are created by the research team and validated by an independent database expert not involved in subsequent evaluation. Validation criteria:

1. All tables in 3NF (no transitive functional dependencies)
2. All tables have a primary key (single-column or composite)
3. All foreign keys reference existing primary keys
4. Column data types are appropriate for the domain
5. NOT NULL is specified for all semantically required columns
6. Table and column names follow consistent snake_case convention

---

## 3. Evaluation Rubric for Experts (RQ1)

### 3.1 Dimensions

Each schema is rated on 5 dimensions using a 5-point Likert scale:

| Dimension | 1 (Poor) | 2 (Below Average) | 3 (Adequate) | 4 (Good) | 5 (Excellent) |
|---|---|---|---|---|---|
| **D1: 3NF Compliance** | Multiple tables violate 2NF or 3NF; severe redundancy | Some transitive dependencies present | No 2NF violations; minor 3NF issues | All tables 3NF; minor cosmetic issues | Perfect 3NF; optimal decomposition |
| **D2: Naming Quality** | Inconsistent style, unclear abbreviations, non-descriptive names | Mixed conventions, some unclear names | Consistent snake_case; names are understandable | Clear, descriptive names; good consistency | Excellent names that convey semantics without comments |
| **D3: Constraint Coverage** | Missing PKs, no FKs, no NOT NULL on required columns | Some PKs present but FKs largely missing | All tables have PKs; most FKs and NOT NULL specified | All PKs, FKs, NOT NULL correctly specified | Comprehensive constraints including UNIQUE and defaults |
| **D4: Relationship Accuracy** | Wrong cardinalities, missing relationships, phantom relationships | Some relationships correct but several errors | Most relationships correct; minor cardinality issues | All relationships present and correct; appropriate types | Perfect relationships with correct cascade semantics implied |
| **D5: Domain Alignment** | Schema does not model the described domain | Major entities or attributes missing | All key entities present; some minor attributes missing | All entities and attributes present; good domain fit | Schema exceeds expectations; anticipates unstated needs |

### 3.2 Scoring Procedure

1. Each expert receives anonymised schema printouts in random order
2. Experts work independently (no communication between raters)
3. Each schema is scored on all 5 dimensions
4. Scores are recorded in a standardised spreadsheet
5. Experts may add free-text comments for any rating below 3

### 3.3 Inter-Rater Agreement

With three raters and ordinal five-point scores, the primary agreement statistic is Krippendorff's alpha with ordinal distance, computed per dimension and overall. Pairwise weighted Cohen's kappa may be reported only as a secondary diagnostic; averaging pairwise kappas is not the confirmatory statistic.

Reported metrics:

- Ordinal Krippendorff's alpha per dimension and overall, with bootstrap 95% confidence intervals
- Percentage of exact agreement across all raters
- Percentage of adjacent agreement (maximum rating difference at most 1)
- Pairwise weighted Cohen's kappa as a labelled sensitivity analysis

---

## 4. Cell-Level Comparison Methodology (RQ2)

### 4.1 Comparison Script

An automated Python script performs cell-level comparison between each generated database and the ground-truth database:

```
For each table T in the schema:
  For each primary key value in ground truth:
    Fetch corresponding row from generated database
    For each column C in T:
      Compare generated_cell vs ground_truth_cell
      Classify as:
        - EXACT_MATCH: identical after type-appropriate normalisation
        - TYPE_CONSISTENT: different string but same semantic value (e.g., "1.0" vs "1", "TRUE" vs "true")
        - NULL_IN_SOURCE: cell is NULL in generated but has value in ground truth
        - WRONG_VALUE: different non-null, non-consistent value
        - MISSING_ROW: entire row not found (PK not present in generated)
        - EXTRA_ROW: row exists in generated but not in ground truth
  For each row in generated that has no matching PK in ground truth:
    Count as EXTRA_ROW
```

### 4.2 Normalisation Rules

Before comparison, values are normalised:

- **Numeric:** `"1.0"` = `"1"` = `1` = `1.0`
- **Boolean:** `"TRUE"`, `"true"`, `"True"`, `"1"`, `"t"` are equivalent (same for false)
- **Date/Time:** `"2024-01-05"` = `"2024-1-5"` = `"05/01/2024"` (ISO only, not ambiguous formats)
- **String:** Whitespace-trimmed; case-sensitive (database default)
- **NULL / empty string:** `NULL` ≠ `""` (treated as different — NULL indicates missing data, empty string is a deliberate value)

---

## 5. Error Typology Classification

| Error Type | Code | Description | Example |
|---|---|---|---|
| Exact Match | OK | Cell value identical after normalisation | Ground: 42, Generated: 42 |
| Type-Consistent | TC | Different representation, same value | Ground: 1.00, Generated: 1 |
| NULL in Source | NS | Generated has NULL where ground has value | Ground: "Smith", Generated: NULL |
| Wrong Value | WV | Generated has a different non-null value | Ground: "Smith", Generated: "Jones" |
| Missing Row | MR | Row with this PK does not exist in generated | Ground has student ID 101, generated does not |
| Extra Row | ER | Row exists in generated but not in ground truth | Generated has student ID 999, ground does not |
| FK Violation | FK | Inserted row has FK value with no matching PK | Generated has `course_id=55` but no course with ID 55 |
| Type Mismatch | TM | Value present but wrong data type | Column is INTEGER, generated stores "N/A" |

---

## 6. Automated Metrics (RQ2)

### 6.1 Per-Table Metrics

Let:
- `TP` = cells that match exactly (EXACT_MATCH) or are type-consistent (TYPE_CONSISTENT)
- `FP` = cells that are WRONG_VALUE or FK_VIOLATION or TYPE_MISMATCH
- `FN` = cells that are NULL_IN_SOURCE or MISSING_ROW
- `Precision` = TP / (TP + FP)
- `Recall` = TP / (TP + FN)
- `F1` = 2 × Precision × Recall / (Precision + Recall)

### 6.2 Global Metrics

- **Overall Precision, Recall, F1** — macro-averaged across all tables
- **Duplicate Rate** — percentage of rows that have duplicate primary keys (computed by `MetricsService.data_quality()`)
- **Normalisation Score** — percentage of tables in 3NF (from `MetricsService.check_3nf()`)
- **Relationship F1** — precision, recall, F1 for identified vs. expected relationships (from `MetricsService.relationship_f1()`)

### 6.3 Normalisation Checks

The `check_3nf()` method evaluates:
- Each table has a primary key
- No transitive dependencies exist (non-key attributes depend only on candidate keys)
- For tables with composite primary keys, no partial dependencies exist (2NF check implicitly)

The automated check is a screening heuristic, not proof of 3NF: functional dependencies that are not represented as constraints cannot be inferred reliably from column flags alone [9]. Confirmatory 3NF labels are based on the documented functional dependencies in each gold standard and independent expert review.

### 6.4 Schema and Relationship Alignment

Before computing key or relationship F1, generated and gold entities are aligned using a frozen two-stage procedure:

1. exact normalised-name match (case-folding, snake-case normalisation, singular/plural normalisation);
2. blind adjudication by two reviewers for remaining semantic synonyms, without access to condition labels or outcome scores.

The alignment table is versioned and reused for every run. A relationship match requires aligned source table, source column, target table, target column, and cardinality. Reversing an equivalent one-to-many edge is normalised before scoring; partial table-only matches are not true positives.

---

## 7. Statistical Methods

### 7.1 Inter-Rater Agreement (RQ1)

- **Primary:** Krippendorff's alpha with ordinal distance across all three raters
- **Reported as:** alpha with bootstrap 95% confidence interval, per dimension and overall
- **Decision rule:** alpha ≥ 0.80 supports confirmatory interpretation; 0.67–0.79 supports tentative conclusions with disagreement analysis; below 0.67 triggers rubric revision or descriptive reporting
- **Secondary:** Pairwise quadratic-weighted Cohen's kappa for diagnosis only
- **Software:** Python `krippendorff` package (primary) and `sklearn.metrics.cohen_kappa_score` (secondary)

### 7.2 Comparing Conditions (RQ1, RQ3)

- **Primary test:** Independent-samples t-test (two-tailed, α = 0.05)
- **Assumption check:** Shapiro-Wilk for normality, Levene's test for equality of variances
- **Non-parametric backup:** Mann-Whitney U test
- **Effect size:** Cohen's d
- **Confidence intervals:** 95% CI for the mean difference

### 7.3 Confidence Intervals (RQ2)

- **Per-metric CI:** Wilson score interval for precision/recall/F1
- **Reported as:** Metric ± CI (e.g., F1 = 0.87 ± 0.03)
- **Bootstrap CI:** 10,000 resamples for the overall mean F1

### 7.4 Multiple Comparison Correction

For the 5-dimension expert evaluation (RQ1), Bonferroni correction is applied:
- Adjusted α = 0.05 / 5 = 0.01 for each dimension
- Both unadjusted and adjusted results are reported

---

## 8. Materials for Experts

Each expert reviewer receives:

1. **Rating instructions** (this protocol)
2. **Anonymised schema printouts** (30 schemas, each on 1–3 pages)
3. **Score recording spreadsheet** (pre-formatted with dropdown menus)
4. **Example schema** (from an unrelated domain) with annotated ratings as training

Total time commitment per expert: approximately 4–6 hours (10–12 minutes per schema).

---

## 9. Automated Evaluation Pipeline

The evaluation script (`backend/evaluate_population.py`) implements the cell-level comparison in section 4, normalisation rules in section 4.2, error typology in section 5, and the precision/recall/F1 metrics (Wilson score intervals) in sections 6-7. It is executed as:

```bash
cd backend
python evaluate_population.py \
  --generated-db projects/{id}/database.sqlite \
  --ground-truth data/datasets/{dataset}/ground_truth.db \
  --gold-schema data/datasets/{dataset}/gold_schema.json \
  --output reports/{id}_report.json
```

The core logic lives in `backend/app/evaluation/population_evaluation.py` and is covered by `backend/tests/test_population_evaluation.py`. Rows are aligned by primary-key columns from the gold schema (falling back to all columns when a table has no declared PK); foreign-key violations are detected against the ground-truth PK values.

Output format:

```json
{
  "project_id": "...",
  "dataset": "hospital",
  "condition": "ai_only",
  "per_table": {
    "patients": {
      "exact": 150,
      "type_consistent": 3,
      "null_in_source": 2,
      "wrong_value": 5,
      "missing_rows": 0,
      "extra_rows": 1,
      "total_cells": 160,
      "precision": 0.97,
      "recall": 0.97,
      "f1": 0.97
    }
  },
  "global": {
    "precision": 0.96,
    "recall": 0.94,
    "f1": 0.95,
    "duplicate_rate": 0.01,
    "norm3_score": 1.0,
    "relationship_f1": 0.89
  }
}
```

---

## 10. References

[1] E. F. Codd. "A Relational Model of Data for Large Shared Data Banks." *Communications of the ACM*, 13(6):377–387, 1970. DOI: 10.1145/362384.362685.

[2] E. F. Codd. "Further Normalization of the Data Base Relational Model." In *Data Base Systems*, Prentice-Hall, 1972. (Origin of 3NF.)

[3] Y. Huhtala, J. Kärkkäinen, P. Porkka, and H. Toivonen. "TANE: An Efficient Algorithm for Discovering Functional and Approximate Dependencies." *The Computer Journal*, 42(2):100–111, 1999. DOI: 10.1093/comjnl/42.2.100.

[4] S. G. Hart and L. E. Staveland. "Development of NASA-TLX (Task Load Index)." *Human Mental Workload*, pages 139–183, 1988.

[5] J. Brooke. "SUS: A Quick and Dirty Usability Scale." *Usability Evaluation in Industry*, pages 189–194, 1996.

[6] K. Krippendorff. *Content Analysis: An Introduction to Its Methodology*, 4th ed. SAGE, 2018. (Ordinal inter-rater agreement, Section 7.1.)

[7] S. S. Shapiro and M. B. Wilk. "An Analysis of Variance Test for Normality (Complete Samples)." *Biometrika*, 52(3/4):591–611, 1965.

[8] H. Levene. "Robust Tests for Equality of Variances." In *Contributions to Probability and Statistics*, Stanford University Press, 1960.

[9] T. Papenbrock et al. "Functional Dependency Discovery: An Experimental Evaluation of Seven Algorithms." *Proceedings of the VLDB Endowment*, 8(10):1082–1093, 2015. (Cited for the screening-heuristic caveat in Section 6.3.)

[10] E. B. Wilson. "Probable Inference, the Law of Succession, and Statistical Inference." *Journal of the American Statistical Association*, 22(158):209–212, 1927.

*Methodological lineage: the benchmark design (gold standard, cell-level comparison, expert rubric) follows the text-to-SQL evaluation conventions of Spider [11] and extends the semantic-parsing evaluation tradition; dataset complexity gradation follows the Spider multi-domain cross-schema design.*

[11] T. Yu et al. "Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task." *EMNLP*, pages 3911–3921, 2018.
