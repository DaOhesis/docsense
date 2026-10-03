"""Evaluation and benchmarking module for the docint pipeline."""
from docint.evaluation.metrics import (
    compute_cer,
    compute_wer,
    evaluate_classification,
    evaluate_document,
    evaluate_fields,
    levenshtein_distance,
    normalize_amount,
    normalize_date,
    normalize_text,
)

__all__ = [
    "levenshtein_distance",
    "compute_cer",
    "compute_wer",
    "normalize_text",
    "normalize_amount",
    "normalize_date",
    "evaluate_fields",
    "evaluate_classification",
    "evaluate_document",
]
