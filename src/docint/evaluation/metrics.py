"""Evaluation metrics engine for OCR, classification, and field extraction.

Pure Python & standard library implementation with zero external heavy dependencies.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Optional

from docint.db.service import parse_amount, parse_date
from docint.schemas import DocType, DocumentResult, ExtractedField, Table


# ---------------------------------------------------------------------------
# 1. Levenshtein Distance & OCR Metrics (CER & WER)
# ---------------------------------------------------------------------------

def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the minimum edit distance between two sequences of characters or tokens.

    Supports insertions, deletions, and substitutions with unit cost.
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    len_s1, len_s2 = len(s1), len(s2)
    # Maintain only two rows to keep memory usage minimal O(len_s2)
    v0 = list(range(len_s2 + 1))
    v1 = [0] * (len_s2 + 1)

    for i in range(len_s1):
        v1[0] = i + 1
        for j in range(len_s2):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0, v1 = v1, v0

    return v0[len_s2]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER).

    CER = (Substitutions + Deletions + Insertions) / (Length of Reference).
    Returns 0.0 if both strings are empty.
    """
    ref = reference.strip()
    hyp = hypothesis.strip()
    if not ref and not hyp:
        return 0.0
    if not ref:
        return float(len(hyp))
    dist = levenshtein_distance(ref, hyp)
    return float(dist) / float(len(ref))


def compute_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER) using whitespace tokenization."""
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words and not hyp_words:
        return 0.0
    if not ref_words:
        return float(len(hyp_words))

    # Apply Levenshtein on word tokens
    len_ref = len(ref_words)
    len_hyp = len(hyp_words)
    v0 = list(range(len_hyp + 1))
    v1 = [0] * (len_hyp + 1)

    for i in range(len_ref):
        v1[0] = i + 1
        for j in range(len_hyp):
            cost = 0 if ref_words[i] == hyp_words[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0, v1 = v1, v0

    return float(v0[len_hyp]) / float(len_ref)


# ---------------------------------------------------------------------------
# 2. Normalization Helpers
# ---------------------------------------------------------------------------

def normalize_text(text: Optional[str]) -> str:
    """Normalize text by stripping whitespace, collapsing multiple spaces, and lowercasing."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return cleaned


def normalize_amount(value: Optional[str]) -> Optional[float]:
    """Parse and normalize monetary amounts."""
    return parse_amount(value)


def normalize_date(value: Optional[str]) -> Optional[str]:
    """Normalize date strings to ISO YYYY-MM-DD."""
    return parse_date(value)


# ---------------------------------------------------------------------------
# 3. Field Extraction Evaluation
# ---------------------------------------------------------------------------

AMOUNT_FIELDS = {"total", "subtotal", "tax", "balance", "amount_due", "net_amount"}
DATE_FIELDS = {"date", "due_date", "invoice_date", "issued_date"}


def fields_match(
    field_name: str,
    gt_val: Optional[str],
    pred_val: Optional[str],
    normalized: bool = True,
) -> bool:
    """Check if predicted field matches ground truth."""
    if gt_val is None and pred_val is None:
        return True
    if gt_val is None or pred_val is None:
        return False

    if not normalized:
        return gt_val.strip() == pred_val.strip()

    # Amount normalization
    if field_name.lower() in AMOUNT_FIELDS:
        gt_num = normalize_amount(gt_val)
        pred_num = normalize_amount(pred_val)
        if gt_num is not None and pred_num is not None:
            return abs(gt_num - pred_num) < 0.01

    # Date normalization
    if field_name.lower() in DATE_FIELDS:
        gt_d = normalize_date(gt_val)
        pred_d = normalize_date(pred_val)
        if gt_d is not None and pred_d is not None:
            return gt_d == pred_d

    # Generic string normalization
    return normalize_text(gt_val) == normalize_text(pred_val)


def evaluate_fields(
    ground_truth_fields: dict[str, ExtractedField],
    predicted_fields: dict[str, ExtractedField],
    normalized: bool = True,
) -> dict[str, Any]:
    """Evaluate extraction accuracy across fields.

    Calculates TP, FP, FN, Precision, Recall, and F1 per field and in micro/macro aggregate.
    """
    all_keys = set(ground_truth_fields.keys()) | set(predicted_fields.keys())
    per_field: dict[str, dict[str, Any]] = {}

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for key in sorted(all_keys):
        gt_field = ground_truth_fields.get(key)
        pred_field = predicted_fields.get(key)

        gt_val = gt_field.value if gt_field else None
        pred_val = pred_field.value if pred_field else None

        tp, fp, fn = 0, 0, 0

        if gt_val is not None and pred_val is not None:
            if fields_match(key, gt_val, pred_val, normalized=normalized):
                tp = 1
            else:
                fp = 1
                fn = 1
        elif gt_val is not None and pred_val is None:
            fn = 1
        elif gt_val is None and pred_val is not None:
            fp = 1

        total_tp += tp
        total_fp += fp
        total_fn += fn

        prec = float(tp) / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
        rec = float(tp) / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2.0 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_field[key] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "gt_value": gt_val,
            "pred_value": pred_val,
            "matched": (tp == 1),
        }

    # Micro average
    micro_p = float(total_tp) / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r = float(total_tp) / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (2.0 * micro_p * micro_r) / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0

    # Macro average
    if per_field:
        macro_f1 = sum(m["f1"] for m in per_field.values()) / len(per_field)
    else:
        macro_f1 = 1.0

    return {
        "per_field": per_field,
        "micro": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(micro_p, 4),
            "recall": round(micro_r, 4),
            "f1": round(micro_f1, 4),
        },
        "macro_f1": round(macro_f1, 4),
    }


# ---------------------------------------------------------------------------
# 4. Classification Evaluation
# ---------------------------------------------------------------------------

def evaluate_classification(
    ground_truth_types: list[DocType],
    predicted_types: list[DocType],
) -> dict[str, Any]:
    """Compute classification accuracy, per-class metrics, and macro F1."""
    if not ground_truth_types:
        return {"accuracy": 0.0, "macro_f1": 0.0, "per_class": {}}

    classes = sorted(list({t.value if isinstance(t, DocType) else str(t) for t in ground_truth_types + predicted_types}))
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    correct = 0
    total = len(ground_truth_types)

    for gt, pred in zip(ground_truth_types, predicted_types):
        gt_str = gt.value if isinstance(gt, DocType) else str(gt)
        pred_str = pred.value if isinstance(pred, DocType) else str(pred)

        if gt_str == pred_str:
            correct += 1
            tp[gt_str] += 1
        else:
            fp[pred_str] += 1
            fn[gt_str] += 1

    accuracy = float(correct) / float(total) if total > 0 else 0.0

    per_class: dict[str, dict[str, Any]] = {}
    f1_sum = 0.0
    for c in classes:
        c_tp = tp[c]
        c_fp = fp[c]
        c_fn = fn[c]
        prec = float(c_tp) / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
        rec = float(c_tp) / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
        f1 = (2.0 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_sum += f1
        per_class[c] = {
            "tp": c_tp,
            "fp": c_fp,
            "fn": c_fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }

    macro_f1 = f1_sum / len(classes) if classes else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "correct": correct,
        "total": total,
        "per_class": per_class,
    }


# ---------------------------------------------------------------------------
# 5. Full Document Evaluation & STP Verification
# ---------------------------------------------------------------------------

def evaluate_document(
    ground_truth: DocumentResult,
    prediction: DocumentResult,
    normalized: bool = True,
) -> dict[str, Any]:
    """Evaluate a single document prediction against ground truth."""
    # 1. Classification match
    type_match = (prediction.doc_type == ground_truth.doc_type)

    # 2. OCR CER / WER if tokens are present
    gt_text = " ".join(t.text for t in ground_truth.ocr).strip()
    pred_text = " ".join(t.text for t in prediction.ocr).strip()
    cer = compute_cer(gt_text, pred_text) if gt_text else None
    wer = compute_wer(gt_text, pred_text) if gt_text else None

    # 3. Field metrics
    field_eval = evaluate_fields(
        ground_truth.fields, prediction.fields, normalized=normalized
    )

    # 4. Straight-Through Processing (STP) check:
    # Requires: needs_review == False, correct doc_type, and all GT fields matched.
    all_fields_matched = all(
        info["matched"]
        for key, info in field_eval["per_field"].items()
        if key in ground_truth.fields and ground_truth.fields[key].value is not None
    )
    is_stp = (not prediction.needs_review) and type_match and all_fields_matched

    return {
        "doc_id": prediction.doc_id,
        "filename": prediction.filename,
        "classification_match": type_match,
        "gt_type": ground_truth.doc_type.value,
        "pred_type": prediction.doc_type.value,
        "cer": round(cer, 4) if cer is not None else None,
        "wer": round(wer, 4) if wer is not None else None,
        "field_evaluation": field_eval,
        "needs_review": prediction.needs_review,
        "is_stp": is_stp,
    }
