# 06 - Benchmark Protocol, Datasets & Expert Evaluation

> **Source Documents**: `docs/11-benchmark-protocol.md`, `docs/16-manual-condition-protocol.md`

---

## 1. Standard Benchmark Datasets

Three standardized domain datasets of increasing complexity are used for experimental evaluation:

| Dataset | Domain | Tables | Columns | FKs | Source Files | Structural Features |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dataset A (Simple)** | University Enrollment | 3 | 10 | 2 | 1 PDF, 1 CSV (30 rows) | Single junction table (`enrollments`), explicit PKs, 1NF-3NF straightforward |
| **Dataset B (Medium)** | Library Management | 5 | 22 | 4 | 1 PDF, 2 CSVs (70 rows) | Implicit relationships, fine calculation logic, overdue constraints |
| **Dataset C (Complex)** | Hospital Management | 8 | 42 | 7 | 1 PDF, 2 CSVs, 1 TXT | Multi-column FKs, cyclic references, treatment-prescription junction tables |

---

## 2. Evaluation Metrics & Formulas

### 2.1 3NF Structural Integrity Score (%)
Measures the proportion of generated tables free of insertion, update, and deletion anomalies:
$$\text{3NF Score} = \frac{N_{\text{3NF}}}{N_{\text{total}}} \times 100\%$$
A table is 3NF compliant if every non-trivial functional dependency $X \to Y$ satisfies either $X$ is a superkey or $Y$ is a prime attribute.

### 2.2 Relationship Precision, Recall & F1-Score
- **Precision**: $P = \frac{|FK_{\text{correct}} \cap FK_{\text{generated}}|}{|FK_{\text{generated}}|}$
- **Recall**: $R = \frac{|FK_{\text{correct}} \cap FK_{\text{generated}}|}{|FK_{\text{gold}}|}$
- **F1-Score**: $F1 = 2 \times \frac{P \times R}{P + R}$

---

## 3. Human-in-the-Loop Expert Rating Rubric

3 independent database domain experts evaluate generated schemas across 5 dimensions on a 5-point Likert scale (1=Poor, 5=Excellent):

1. **D1: 3NF Compliance**: Absence of redundant attributes and transitive dependencies.
2. **D2: Naming Quality**: Consistent `snake_case` naming conventions and domain expressiveness.
3. **D3: Constraint Coverage**: Proper identification of Primary Keys, Foreign Keys, UNIQUE, and NOT NULL constraints.
4. **D4: Relationship Accuracy**: Correct cardinalities (1:N, N:M) and target foreign key definitions.
5. **D5: Domain Alignment**: Semantic completeness matching source document descriptions.

### Inter-Rater Agreement
Inter-rater consensus among experts is measured using **Krippendorff's Alpha ($\alpha$)** with ordinal distance metrics across dimensions.
