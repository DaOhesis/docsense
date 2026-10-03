"""Unit tests for the evaluation framework (metrics, dataset loader, and runner)."""
from __future__ import annotations

import pytest

from docint.evaluation.dataset_loader import convert_sroie_sample, load_labels, save_label
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
from docint.evaluation.runner import evaluate_pipeline, format_cli_report
from docint.schemas import DocType, DocumentResult, ExtractedField, OCRToken


# ---------------------------------------------------------------------------
# 1. Levenshtein Distance & CER/WER
# ---------------------------------------------------------------------------

def test_levenshtein_distance():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("hello", "hello") == 0
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("cat", "cats") == 1
    assert levenshtein_distance("cats", "cat") == 1
    assert levenshtein_distance("cat", "hat") == 1
    assert levenshtein_distance("", "abc") == 3
    assert levenshtein_distance("abc", "") == 3


def test_compute_cer():
    assert compute_cer("", "") == 0.0
    assert compute_cer("INVOICE", "INVOICE") == 0.0
    # "test" (4 chars) -> "best" (1 substitution) -> CER = 1/4 = 0.25
    assert compute_cer("test", "best") == pytest.approx(0.25)
    # Empty ref with 4-char hyp
    assert compute_cer("", "test") == 4.0


def test_compute_wer():
    assert compute_wer("", "") == 0.0
    assert compute_wer("the quick brown fox", "the quick brown fox") == 0.0
    # 4 words, 1 substitution ("dog" -> "fox") -> WER = 1/4 = 0.25
    assert compute_wer("the quick brown fox", "the quick brown dog") == pytest.approx(0.25)
    assert compute_wer("", "one two") == 2.0


# ---------------------------------------------------------------------------
# 2. Normalization Helpers
# ---------------------------------------------------------------------------

def test_normalize_text():
    assert normalize_text("  ACME   TRADERS  ") == "acme traders"
    assert normalize_text(None) == ""
    assert normalize_text("") == ""


def test_normalize_amount():
    assert normalize_amount("$1,180.00") == pytest.approx(1180.00)
    assert normalize_amount("1180.00") == pytest.approx(1180.00)
    assert normalize_amount("invalid") is None


def test_normalize_date():
    assert normalize_date("15/09/2026") == "2026-09-15"
    assert normalize_date("2026-09-15") == "2026-09-15"
    assert normalize_date("invalid") is None


# ---------------------------------------------------------------------------
# 3. Field Evaluation
# ---------------------------------------------------------------------------

def test_evaluate_fields_exact_and_normalized():
    gt = {
        "vendor": ExtractedField(value="ACME Traders"),
        "total": ExtractedField(value="1180.00"),
        "date": ExtractedField(value="2026-09-01"),
    }
    # Predictions with different formatting: currency symbols, spaces, different date format
    pred = {
        "vendor": ExtractedField(value="  acme traders "),
        "total": ExtractedField(value="$ 1,180.00"),
        "date": ExtractedField(value="01/09/2026"),
    }

    # Normalized comparison should match all 3
    norm_res = evaluate_fields(gt, pred, normalized=True)
    assert norm_res["micro"]["precision"] == 1.0
    assert norm_res["micro"]["recall"] == 1.0
    assert norm_res["micro"]["f1"] == 1.0

    # Non-normalized comparison should fail on formatting differences
    raw_res = evaluate_fields(gt, pred, normalized=False)
    assert raw_res["micro"]["f1"] < 1.0


def test_evaluate_fields_missing_and_spurious():
    gt = {
        "vendor": ExtractedField(value="ACME"),
        "total": ExtractedField(value="100.00"),
    }
    # Prediction has wrong total and an extra unrequested field, missing vendor
    pred = {
        "total": ExtractedField(value="999.00"),
        "extra_field": ExtractedField(value="extra"),
    }

    res = evaluate_fields(gt, pred, normalized=True)
    # total: mismatched (FP=1, FN=1)
    # vendor: missing (FN=1)
    # extra_field: spurious (FP=1)
    assert res["micro"]["tp"] == 0
    assert res["micro"]["fp"] == 2
    assert res["micro"]["fn"] == 2
    assert res["micro"]["f1"] == 0.0


# ---------------------------------------------------------------------------
# 4. Classification Evaluation
# ---------------------------------------------------------------------------

def test_evaluate_classification():
    gt = [DocType.invoice, DocType.receipt, DocType.invoice, DocType.form]
    pred = [DocType.invoice, DocType.receipt, DocType.receipt, DocType.form]

    res = evaluate_classification(gt, pred)
    assert res["total"] == 4
    assert res["correct"] == 3
    assert res["accuracy"] == pytest.approx(0.75)
    assert "invoice" in res["per_class"]
    assert res["per_class"]["form"]["f1"] == 1.0


# ---------------------------------------------------------------------------
# 5. Full Document Evaluation & STP
# ---------------------------------------------------------------------------

def test_evaluate_document_stp():
    gt = DocumentResult(
        doc_id="gt-1",
        doc_type=DocType.invoice,
        fields={
            "total": ExtractedField(value="1180.00"),
            "vendor": ExtractedField(value="ACME"),
        },
    )
    pred_ok = DocumentResult(
        doc_id="pred-1",
        doc_type=DocType.invoice,
        fields={
            "total": ExtractedField(value="1180.00"),
            "vendor": ExtractedField(value="ACME"),
        },
        needs_review=False,
    )
    res_ok = evaluate_document(gt, pred_ok)
    assert res_ok["is_stp"] is True

    # If needs_review is True, it should not be considered STP
    pred_needs_review = DocumentResult(
        doc_id="pred-2",
        doc_type=DocType.invoice,
        fields={
            "total": ExtractedField(value="1180.00"),
            "vendor": ExtractedField(value="ACME"),
        },
        needs_review=True,
    )
    res_nr = evaluate_document(gt, pred_needs_review)
    assert res_nr["is_stp"] is False


# ---------------------------------------------------------------------------
# 6. Dataset Loader & SROIE Adapter
# ---------------------------------------------------------------------------

def test_sroie_adapter():
    sroie_data = {
        "company": "BOOK STORE",
        "date": "20/01/2026",
        "total": "55.00",
        "address": "123 Main St",
    }
    doc = convert_sroie_sample("doc-1", "sroie_01.png", sroie_data)
    assert doc.doc_type == DocType.receipt
    assert doc.fields["total"].value == "55.00"
    assert doc.fields["merchant"].value == "BOOK STORE"


def test_cord_adapter():
    from docint.evaluation.dataset_loader import convert_cord_sample
    cord_data = {"merchant": "WARUNG KOPI", "total": "25000", "date": "12/05/2026"}
    doc = convert_cord_sample("cord-1", "cord_01.png", cord_data)
    assert doc.doc_type == DocType.receipt
    assert doc.fields["merchant"].value == "WARUNG KOPI"
    assert doc.fields["total"].value == "25000"


def test_funsd_adapter():
    from docint.evaluation.dataset_loader import convert_funsd_sample
    funsd_data = {
        "form": [
            {"text": "Patient Name", "box": [10, 10, 100, 30], "label": "question"},
            {"text": "John Doe", "box": [110, 10, 200, 30], "label": "answer"},
        ]
    }
    doc = convert_funsd_sample("funsd-1", "funsd_01.png", funsd_data)
    assert doc.doc_type == DocType.form
    assert len(doc.ocr) == 2
    assert "patient_name" in doc.fields


def test_load_labels_and_benchmark_count():
    labels = load_labels("data/labels")
    assert len(labels) >= 30
    # Confirm invoices, receipts, and forms are all represented
    doc_types = {doc.doc_type for doc in labels.values()}
    assert DocType.invoice in doc_types
    assert DocType.receipt in doc_types
    assert DocType.form in doc_types


# ---------------------------------------------------------------------------
# 7. Runner Integration Test
# ---------------------------------------------------------------------------

def test_pipeline_evaluation_runner():
    summary = evaluate_pipeline(labels_dir="data/labels", samples_dir="data/samples")
    assert "error" not in summary
    assert summary["total_documents"] >= 2
    assert "classification" in summary
    assert "field_metrics" in summary
    assert "stp" in summary

    # Verify report formatting
    report = format_cli_report(summary)
    assert "DOCSENSE PIPELINE BENCHMARK" in report
    assert "Classification Acc" in report
