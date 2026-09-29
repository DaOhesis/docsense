# Pipeline Evaluation & Benchmarking Specification

This document defines the official evaluation framework, metrics, target benchmarks, and validation methodology for the **Smart Document & Form Intelligence System** (`docint`).

All module owners (Preprocessing & OCR, Classification, Field Extraction, and Pipeline Integration) must evaluate their models and heuristics against these metrics.

---

## 1. High-Level Metrics Overview

The pipeline is evaluated along four sequential dimensions and one holistic end-to-end operational metric:

| Dimension | Stage Owner | Primary Metric | Target (Production V1) |
| :--- | :--- | :--- | :--- |
| **1. OCR Quality** | Person A | Character Error Rate (CER), Word Error Rate (WER) | CER $< 3.0\%$, WER $< 6.0\%$ |
| **2. Classification** | Person B | Macro $F_1$, Accuracy | Accuracy $> 95.0\%$, Macro $F_1 > 0.92$ |
| **3. Field Extraction** | Person C | Field-Level Precision, Recall, $F_1$ (Normalized) | $F_1 > 90.0\%$ (Key Fields) |
| **4. Table Extraction** | Person C | Row-level Precision, Recall, $F_1$ | Row $F_1 > 85.0\%$ |
| **5. End-to-End STP** | Lead | Straight-Through Processing (STP) Rate | STP Rate $> 80.0\%$ |

---

## 2. Metric Formulations

### 2.1 OCR Quality (CER & WER)

Evaluates text recognition fidelity between ground-truth text $T_{\text{ref}}$ and OCR tokens hypothesis $T_{\text{hyp}}$.

$$\text{CER} = \frac{S_c + D_c + I_c}{N_c}$$

$$\text{WER} = \frac{S_w + D_w + I_w}{N_w}$$

- $S$: Substitutions (Levenshtein edit operations)
- $D$: Deletions
- $I$: Insertions
- $N$: Total characters (or words) in the reference ground truth

*Note: Characters are compared case-sensitively by default, with normalized whitespace.*

---

### 2.2 Document Classification

Evaluates the model's ability to categorize documents into `invoice`, `receipt`, `form`, `certificate`, or `unknown`.

- **Accuracy**: $\frac{\sum \text{Correct}}{\text{Total Documents}}$
- **Precision ($P_c$)**: $\frac{TP_c}{TP_c + FP_c}$ per class $c$.
- **Recall ($R_c$)**: $\frac{TP_c}{TP_c + FN_c}$ per class $c$.
- **Macro $F_1$**: $\frac{1}{|C|} \sum_{c \in C} 2 \cdot \frac{P_c \cdot R_c}{P_c + R_c}$ (treats all classes equally).
- **Micro $F_1$**: Aggregate $TP, FP, FN$ across all classes before computing $F_1$.

---

### 2.3 Key Information Extraction (KIE)

For each field $k \in \{\text{invoice\_no}, \text{date}, \text{vendor}, \text{subtotal}, \text{tax}, \text{total}, \dots\}$:

- **True Positive ($TP$)**: Field was predicted and matches ground truth.
- **False Positive ($FP$)**: Field was predicted with an incorrect value, or predicted when absent in ground truth.
- **False Negative ($FN$)**: Field exists in ground truth but was omitted by the extractor (`value=None` or key missing).

$$P = \frac{TP}{TP + FP}, \quad R = \frac{TP}{TP + FN}, \quad F_1 = 2 \cdot \frac{P \cdot R}{P + R}$$

#### Matching Modes:
1. **Strict Exact Match**: `pred.value.strip() == gt.value.strip()`.
2. **Normalized Match (Default)**:
   - **Amounts** (`total`, `subtotal`, `tax`): Stripped of currency symbols, spaces, and commas; compared as floating-point numbers within $\pm 0.01$ tolerance.
   - **Dates** (`date`, `due_date`): Parsed into ISO format (`YYYY-MM-DD`) before equality check.
   - **Text Strings** (`vendor`, `invoice_no`): Case-insensitive trimmed alphanumeric match.

---

### 2.4 Table Extraction

Line item tables are evaluated on structural correctness and content accuracy:

- **Header Match**: Set equality of column headers (`item`, `qty`, `price`).
- **Row-level $F_1$**: A predicted row is considered a True Positive if all corresponding key cells match ground truth after normalization.

---

### 2.5 End-to-End Straight-Through Processing (STP)

In production, human review incurs time and cost. The pipeline aims to maximize **Zero-Touch Processing**:

A document is classified as **Straight-Through Processed (STP)** if and only if:
1. The pipeline flags `needs_review == False`.
2. The document type is correctly classified.
3. All critical fields (`total`, `date`, `invoice_no`/`merchant`) are correctly extracted with 100% accuracy.

$$\text{STP Rate} = \frac{\text{Count of Valid Unreviewed Documents}}{\text{Total Processed Documents}} \times 100\%$$

---

## 3. Benchmark Datasets

The team evaluates on a combination of open academic datasets and proprietary anonymized samples:

| Dataset | Type | Source / Format | Used For |
| :--- | :--- | :--- | :--- |
| **SROIE** | Scanned Receipts (1,000 imgs) | Task 1 (OCR), Task 3 (Key Information: company, date, total, address) | OCR & Receipt Extraction |
| **CORD** | Indonesian Receipts (1,000 imgs) | Complex multi-tier hierarchical receipts | Layout & Receipt Parsing |
| **FUNSD** | Scanned Forms (199 docs) | Forms with diverse layouts & noisy scans | Form Classification & Key-Value pairs |
| **Local Test Set** | Invoices & Receipts (30 docs) | `data/samples/` with ground-truth in `data/labels/` | Core CI & Regression Testing |

---

## 4. Running the Benchmark

An automated CLI tool is provided to run evaluations:

```bash
# Run evaluation on the local test suite
python -m docint.evaluation.runner --samples-dir data/samples --labels-dir data/labels

# Run OCR-only evaluation
python -m docint.evaluation.runner --stage ocr --samples-dir data/samples --labels-dir data/labels

# Export detailed markdown scorecard
python -m docint.evaluation.runner --report report.md
```
