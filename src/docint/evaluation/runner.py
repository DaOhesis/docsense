"""Evaluation runner CLI for the docint pipeline.

Executes test documents through the pipeline, scores predictions against
canonical ground-truth labels in data/labels/, and outputs a standardized scorecard.

Usage
-----
    python -m docint.evaluation.runner
    python -m docint.evaluation.runner --labels-dir data/labels --report evaluation_report.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is on sys.path when invoked directly
_SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from docint.evaluation.dataset_loader import load_labels
from docint.evaluation.metrics import (
    evaluate_classification,
    evaluate_document,
    evaluate_fields,
)
from docint.pipeline import process_document
from docint.schemas import DocType, DocumentResult


def evaluate_pipeline(
    labels_dir: Path | str = "data/labels",
    samples_dir: Path | str = "data/samples",
    normalized: bool = True,
) -> dict[str, Any]:
    """Run pipeline on available benchmark documents and evaluate against ground truth."""
    labels = load_labels(labels_dir)
    if not labels:
        return {"error": f"No ground truth JSON files found in {labels_dir}"}

    samples_path = Path(samples_dir)
    doc_evals: list[dict[str, Any]] = []

    gt_types: list[DocType] = []
    pred_types: list[DocType] = []

    total_stp = 0

    # Deduplicate labels (since load_labels indexes by stem and filename)
    unique_labels: dict[str, DocumentResult] = {}
    for key, doc in labels.items():
        unique_labels[doc.doc_id] = doc

    for doc_id, gt in unique_labels.items():
        # Check if sample file exists on disk, else mock with dummy bytes
        sample_file = samples_path / gt.filename if gt.filename else None
        if sample_file and sample_file.exists():
            file_bytes = sample_file.read_bytes()
        else:
            file_bytes = b"sample_mock_content"

        # Execute through pipeline
        pred = process_document(file_bytes, gt.filename or "sample.png")

        # Evaluate individual document
        eval_res = evaluate_document(gt, pred, normalized=normalized)
        doc_evals.append(eval_res)

        gt_types.append(gt.doc_type)
        pred_types.append(pred.doc_type)

        if eval_res["is_stp"]:
            total_stp += 1

    total_docs = len(doc_evals)
    clf_metrics = evaluate_classification(gt_types, pred_types)

    # Aggregate field metrics across all documents
    all_gt_fields = {}
    all_pred_fields = {}
    for i, gt in enumerate(unique_labels.values()):
        pred = doc_evals[i]
        for k, v in gt.fields.items():
            all_gt_fields[f"{gt.doc_id}_{k}"] = v
        # Extract pred fields from corresponding prediction
        pred_field_map = pred["field_evaluation"]["per_field"]
        for k, v in pred_field_map.items():
            if v["pred_value"] is not None:
                from docint.schemas import ExtractedField
                all_pred_fields[f"{gt.doc_id}_{k}"] = ExtractedField(value=v["pred_value"])

    aggregated_fields = evaluate_fields(all_gt_fields, all_pred_fields, normalized=normalized)
    stp_rate = (float(total_stp) / float(total_docs) * 100.0) if total_docs > 0 else 0.0

    return {
        "total_documents": total_docs,
        "classification": clf_metrics,
        "field_metrics": aggregated_fields,
        "stp": {
            "total_stp": total_stp,
            "total_documents": total_docs,
            "stp_rate_pct": round(stp_rate, 2),
        },
        "document_evaluations": doc_evals,
    }


def format_cli_report(summary: dict[str, Any]) -> str:
    """Format evaluation summary into a readable CLI terminal report."""
    if "error" in summary:
        return f"\n[!] Evaluation Error: {summary['error']}\n"

    lines = []
    lines.append("=" * 68)
    lines.append("         DOCSENSE PIPELINE BENCHMARK & EVALUATION REPORT        ")
    lines.append("=" * 68)

    total = summary["total_documents"]
    lines.append(f"Documents Evaluated : {total}")
    lines.append(f"Classification Acc  : {summary['classification']['accuracy'] * 100:.1f}%")
    lines.append(f"Classification Macro-F1: {summary['classification']['macro_f1']:.4f}")
    lines.append(f"Field Micro-F1      : {summary['field_metrics']['micro']['f1']:.4f}")
    lines.append(f"Field Macro-F1      : {summary['field_metrics']['macro_f1']:.4f}")
    lines.append(
        f"STP Rate (Zero-Touch): {summary['stp']['stp_rate_pct']:.1f}% "
        f"({summary['stp']['total_stp']}/{summary['stp']['total_documents']})"
    )
    lines.append("-" * 68)

    # Classification breakdown
    lines.append("\n[Classification Breakdown]")
    lines.append(f"{'Class':<15} {'Precision':<12} {'Recall':<12} {'F1-Score':<10}")
    lines.append("-" * 50)
    for cls_name, m in summary["classification"]["per_class"].items():
        lines.append(f"{cls_name:<15} {m['precision']:<12.4f} {m['recall']:<12.4f} {m['f1']:<10.4f}")

    # Field metrics summary
    lines.append("\n[Field Extraction Summary]")
    lines.append(f"True Positives  : {summary['field_metrics']['micro']['tp']}")
    lines.append(f"False Positives : {summary['field_metrics']['micro']['fp']}")
    lines.append(f"False Negatives : {summary['field_metrics']['micro']['fn']}")
    lines.append(f"Precision       : {summary['field_metrics']['micro']['precision']:.4f}")
    lines.append(f"Recall          : {summary['field_metrics']['micro']['recall']:.4f}")
    lines.append(f"Micro F1        : {summary['field_metrics']['micro']['f1']:.4f}")
    lines.append("=" * 68)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate DocSense pipeline against ground-truth labels.")
    parser.add_argument("--labels-dir", default="data/labels", help="Directory with ground-truth JSON files")
    parser.add_argument("--samples-dir", default="data/samples", help="Directory with input document samples")
    parser.add_argument("--report", default=None, help="Optional path to output markdown report file")

    args = parser.parse_args()

    summary = evaluate_pipeline(labels_dir=args.labels_dir, samples_dir=args.samples_dir)
    report_text = format_cli_report(summary)
    print(report_text)

    if args.report and "error" not in summary:
        report_path = Path(args.report)
        report_path.write_text(f"```\n{report_text}\n```\n", encoding="utf-8")
        print(f"\n[+] Detailed report saved to {report_path.resolve()}")


if __name__ == "__main__":
    main()
