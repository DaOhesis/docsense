"""Dataset loader, downloader, and benchmark annotation utilities for the evaluation framework.

Supports:
- Loading and saving ground-truth DocumentResult files (data/labels/*.json).
- Adapters for common public Document AI benchmarks:
    - SROIE (Scanned Receipts OCR and Information Extraction)
    - CORD (Consolidated Receipt Dataset)
    - FUNSD (Form Understanding in Noisy Scanned Documents)
- Builder for the official 30-document ground-truth benchmark suite.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Optional

from docint.schemas import DocType, DocumentResult, ExtractedField, OCRToken, Table, ValidationResult


def load_labels(labels_dir: Path | str) -> dict[str, DocumentResult]:
    """Load all JSON label files from a directory into a map of filename -> DocumentResult."""
    path = Path(labels_dir)
    results: dict[str, DocumentResult] = {}
    if not path.exists():
        return results

    for file in sorted(path.glob("*.json")):
        try:
            content = file.read_text(encoding="utf-8")
            doc = DocumentResult.model_validate_json(content)
            results[file.stem] = doc
            if doc.filename:
                results[doc.filename] = doc
        except Exception:
            continue
    return results


def save_label(label: DocumentResult, target_path: Path | str) -> None:
    """Save a DocumentResult instance as a canonical ground-truth JSON file."""
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(label.model_dump_json(indent=2), encoding="utf-8")


def convert_sroie_sample(
    doc_id: str,
    filename: str,
    sroie_json: dict[str, str],
    ocr_lines: list[tuple[str, list[float]]] | None = None,
) -> DocumentResult:
    """Convert an SROIE ground-truth annotation to DocumentResult contract.

    SROIE format: {"company": "...", "date": "...", "address": "...", "total": "..."}
    """
    fields: dict[str, ExtractedField] = {}
    if "company" in sroie_json:
        fields["merchant"] = ExtractedField(value=sroie_json["company"], conf=1.0)
        fields["vendor"] = ExtractedField(value=sroie_json["company"], conf=1.0)
    if "date" in sroie_json:
        fields["date"] = ExtractedField(value=sroie_json["date"], conf=1.0)
    if "total" in sroie_json:
        fields["total"] = ExtractedField(value=sroie_json["total"], conf=1.0)
    if "address" in sroie_json:
        fields["address"] = ExtractedField(value=sroie_json["address"], conf=1.0)

    ocr_tokens: list[OCRToken] = []
    if ocr_lines:
        for text, bbox in ocr_lines:
            ocr_tokens.append(OCRToken(text=text, bbox=bbox, conf=1.0))

    return DocumentResult(
        doc_id=doc_id,
        filename=filename,
        doc_type=DocType.receipt,
        doc_type_conf=1.0,
        ocr=ocr_tokens,
        fields=fields,
        tables=[],
        validation=[],
        needs_review=False,
    )


def convert_cord_sample(
    doc_id: str,
    filename: str,
    cord_json: dict[str, Any],
) -> DocumentResult:
    """Convert CORD receipt annotation to DocumentResult."""
    fields: dict[str, ExtractedField] = {}
    valid_keys = {"merchant", "total", "subtotal", "tax", "date"}

    for key, val in cord_json.items():
        if key in valid_keys and isinstance(val, (str, int, float)):
            fields[key] = ExtractedField(value=str(val), conf=1.0)

    return DocumentResult(
        doc_id=doc_id,
        filename=filename,
        doc_type=DocType.receipt,
        doc_type_conf=1.0,
        ocr=[],
        fields=fields,
        tables=[],
        validation=[],
        needs_review=False,
    )


def convert_funsd_sample(
    doc_id: str,
    filename: str,
    funsd_json: dict[str, Any],
) -> DocumentResult:
    """Convert FUNSD form annotation to DocumentResult."""
    fields: dict[str, ExtractedField] = {}
    ocr_tokens: list[OCRToken] = []

    for item in funsd_json.get("form", []):
        text = item.get("text", "")
        box = item.get("box", [0, 0, 100, 100])
        label = item.get("label", "other")
        if len(box) == 4:
            ocr_tokens.append(OCRToken(text=text, bbox=[float(b) for b in box], conf=1.0))
        if label in ("question", "header") and text:
            clean_key = "".join(c if c.isalnum() else "_" for c in text.lower())[:30].strip("_")
            if clean_key:
                fields[clean_key] = ExtractedField(value=text, conf=1.0)

    return DocumentResult(
        doc_id=doc_id,
        filename=filename,
        doc_type=DocType.form,
        doc_type_conf=1.0,
        ocr=ocr_tokens,
        fields=fields,
        tables=[],
        validation=[],
        needs_review=False,
    )


def build_standard_30_test_set(output_dir: Path | str = "data/labels") -> list[DocumentResult]:
    """Build and save the official 30-document ground-truth benchmark suite:

    - 15 Invoices: diverse layouts, dates, vendors, tax rules, and line items.
    - 10 Receipts: retail, dining, travel, grocery, fuel, payment methods.
    - 5 Forms / Certificates: tax forms, application forms, compliance certificates.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    documents: list[DocumentResult] = []

    # -----------------------------------------------------------------------
    # 1. 15 INVOICES
    # -----------------------------------------------------------------------
    invoices_data = [
        ("inv-001", "invoice_001.png", "Apex Industrial Supplies", "INV-2026-001", "2026-01-10", "1500.00", "270.00", "1770.00", [["Steel Bolts M8", "100", "10.00"], ["Hydraulic Fluid 5L", "2", "250.00"]]),
        ("inv-002", "invoice_002.png", "CloudScale Hosting Ltd", "CS-88910", "2026-01-15", "450.00", "81.00", "531.00", [["Dedicated Server Tier 2", "1", "450.00"]]),
        ("inv-003", "invoice_003.png", "Quantum Logistics Corp", "QL-9921", "2026-01-20", "2200.00", "396.00", "2596.00", [["Freight Transit (Sea)", "1", "2200.00"]]),
        ("inv-004", "invoice_004.png", "BlueRiver Office Supplies", "BRO-4040", "2026-01-28", "320.00", "57.60", "377.60", [["A4 Paper Reams (5x)", "10", "20.00"], ["Ergonomic Mouse", "4", "30.00"]]),
        ("inv-005", "invoice_005.png", "Vanguard Security Systems", "VSS-1020", "2026-02-05", "1800.00", "324.00", "2124.00", [["CCTV Dome Camera 4K", "6", "300.00"]]),
        ("inv-006", "invoice_006.png", "CleanWater Solutions", "CW-5510", "2026-02-12", "680.00", "122.40", "802.40", [["Industrial Filter Cartridge", "4", "170.00"]]),
        ("inv-007", "invoice_007.png", "Nordic Timber Imports", "NT-7741", "2026-02-18", "4100.00", "738.00", "4838.00", [["Oak Planks 2x4", "50", "82.00"]]),
        ("inv-008", "invoice_008.png", "Silicon Valley Micro", "SVM-303", "2026-02-25", "12500.00", "2250.00", "14750.00", [["Embedded Controller Unit", "50", "250.00"]]),
        ("inv-009", "invoice_009.png", "Precision Engineering Works", "PEW-619", "2026-03-02", "3400.00", "612.00", "4012.00", [["CNC Milling Service", "20", "170.00"]]),
        ("inv-010", "invoice_010.png", "Atlas Packaging Co", "APC-808", "2026-03-09", "750.00", "135.00", "885.00", [["Cardboard Boxes XL", "500", "1.50"]]),
        ("inv-011", "invoice_011.png", "Starlight Media Agency", "SMA-112", "2026-03-15", "5000.00", "900.00", "5900.00", [["Brand Strategy Consultation", "1", "5000.00"]]),
        ("inv-012", "invoice_012.png", "GreenField Organic Seeds", "GOS-901", "2026-03-22", "890.00", "160.20", "1050.20", [["Wheat Seed Bags (50kg)", "10", "89.00"]]),
        ("inv-013", "invoice_013.png", "Delta Electrical Corp", "DEC-334", "2026-03-29", "1620.00", "291.60", "1911.60", [["Copper Wire Spool 100m", "6", "270.00"]]),
        ("inv-014", "invoice_014.png", "Summit Facilities Management", "SFM-710", "2026-04-05", "2800.00", "504.00", "3304.00", [["HVAC Quarterly Maintenance", "1", "2800.00"]]),
        ("inv-015", "invoice_015.png", "Metro Fleet Maintenance", "MFM-552", "2026-04-12", "1400.00", "252.00", "1652.00", [["Brake Pad Replacement", "4", "350.00"]]),
    ]

    for doc_id, filename, vendor, inv_no, inv_date, subtotal, tax, total, items in invoices_data:
        ocr_tokens = [
            OCRToken(text="INVOICE", bbox=[20.0, 20.0, 150.0, 50.0], conf=0.99),
            OCRToken(text=vendor, bbox=[20.0, 60.0, 250.0, 85.0], conf=0.98),
            OCRToken(text=f"Invoice No: {inv_no}", bbox=[300.0, 20.0, 450.0, 45.0], conf=0.97),
            OCRToken(text=f"Date: {inv_date}", bbox=[300.0, 50.0, 420.0, 75.0], conf=0.97),
            OCRToken(text=f"Subtotal: {subtotal}", bbox=[300.0, 300.0, 450.0, 325.0], conf=0.96),
            OCRToken(text=f"Tax: {tax}", bbox=[300.0, 330.0, 450.0, 355.0], conf=0.96),
            OCRToken(text=f"Total: {total}", bbox=[300.0, 360.0, 450.0, 390.0], conf=0.98),
        ]
        fields = {
            "vendor": ExtractedField(value=vendor, conf=1.0, bbox=[20.0, 60.0, 250.0, 85.0]),
            "invoice_no": ExtractedField(value=inv_no, conf=1.0, bbox=[300.0, 20.0, 450.0, 45.0]),
            "date": ExtractedField(value=inv_date, conf=1.0, bbox=[300.0, 50.0, 420.0, 75.0]),
            "subtotal": ExtractedField(value=subtotal, conf=1.0, bbox=[300.0, 300.0, 450.0, 325.0]),
            "tax": ExtractedField(value=tax, conf=1.0, bbox=[300.0, 330.0, 450.0, 355.0]),
            "total": ExtractedField(value=total, conf=1.0, bbox=[300.0, 360.0, 450.0, 390.0]),
        }
        tables = [Table(headers=["item", "qty", "price"], rows=items)]
        val = [ValidationResult(rule="total_matches", passed=True, message="")]
        doc = DocumentResult(
            doc_id=doc_id,
            filename=filename,
            doc_type=DocType.invoice,
            doc_type_conf=0.98,
            ocr=ocr_tokens,
            fields=fields,
            tables=tables,
            validation=val,
            needs_review=False,
        )
        save_label(doc, out_path / f"{doc_id}.json")
        documents.append(doc)

    # -----------------------------------------------------------------------
    # 2. 10 RECEIPTS
    # -----------------------------------------------------------------------
    receipts_data = [
        ("rec-001", "receipt_001.png", "Central Supermarket", "2026-01-12", "68.45", "Credit Card"),
        ("rec-002", "receipt_002.png", "Corner Bakery & Cafe", "2026-01-18", "14.20", "Cash"),
        ("rec-003", "receipt_003.png", "Shell Express Fuel", "2026-01-25", "52.00", "Debit Card"),
        ("rec-004", "receipt_004.png", "Bistro Bella Italia", "2026-02-02", "112.50", "MasterCard"),
        ("rec-005", "receipt_005.png", "City Taxi Transit", "2026-02-14", "28.75", "Contactless"),
        ("rec-006", "receipt_006.png", "Walnut Pharmacy", "2026-02-22", "34.10", "Cash"),
        ("rec-007", "receipt_007.png", "HomeHardware Depot", "2026-03-05", "185.90", "Credit Card"),
        ("rec-008", "receipt_008.png", "Espresso Barista Co", "2026-03-12", "8.50", "Apple Pay"),
        ("rec-009", "receipt_009.png", "Airport Parking Garage", "2026-03-20", "45.00", "Credit Card"),
        ("rec-010", "receipt_010.png", "FreshFruit Daily Market", "2026-03-27", "22.80", "Debit Card"),
    ]

    for doc_id, filename, merchant, r_date, total, pay_method in receipts_data:
        ocr_tokens = [
            OCRToken(text=merchant.upper(), bbox=[30.0, 10.0, 200.0, 35.0], conf=0.99),
            OCRToken(text=f"DATE: {r_date}", bbox=[30.0, 45.0, 160.0, 65.0], conf=0.97),
            OCRToken(text=f"TOTAL: ${total}", bbox=[30.0, 150.0, 180.0, 175.0], conf=0.98),
            OCRToken(text=f"PAYMENT: {pay_method}", bbox=[30.0, 190.0, 190.0, 210.0], conf=0.95),
        ]
        fields = {
            "merchant": ExtractedField(value=merchant, conf=1.0, bbox=[30.0, 10.0, 200.0, 35.0]),
            "vendor": ExtractedField(value=merchant, conf=1.0, bbox=[30.0, 10.0, 200.0, 35.0]),
            "date": ExtractedField(value=r_date, conf=1.0, bbox=[30.0, 45.0, 160.0, 65.0]),
            "total": ExtractedField(value=total, conf=1.0, bbox=[30.0, 150.0, 180.0, 175.0]),
            "payment_method": ExtractedField(value=pay_method, conf=1.0, bbox=[30.0, 190.0, 190.0, 210.0]),
        }
        doc = DocumentResult(
            doc_id=doc_id,
            filename=filename,
            doc_type=DocType.receipt,
            doc_type_conf=0.97,
            ocr=ocr_tokens,
            fields=fields,
            tables=[],
            validation=[],
            needs_review=False,
        )
        save_label(doc, out_path / f"{doc_id}.json")
        documents.append(doc)

    # -----------------------------------------------------------------------
    # 3. 5 FORMS & CERTIFICATES
    # -----------------------------------------------------------------------
    forms_data = [
        ("form-001", "form_001.png", DocType.form, "Patient Intake Form", "Dr. Robert Smith Clinic", "2026-01-08"),
        ("form-002", "form_002.png", DocType.form, "Vendor Registration Form", "Global Procurement Hub", "2026-02-10"),
        ("form-003", "form_003.png", DocType.form, "Equipment Inspection Checklist", "Safety First Audit Corp", "2026-03-01"),
        ("cert-001", "cert_001.png", DocType.certificate, "Certificate of Calibration", "ISO Metrology Labs", "2026-01-20"),
        ("cert-002", "cert_002.png", DocType.certificate, "Certificate of Compliance", "Global Quality Assurance", "2026-02-28"),
    ]

    for doc_id, filename, doc_type, title, issuer, issue_date in forms_data:
        ocr_tokens = [
            OCRToken(text=title.upper(), bbox=[50.0, 20.0, 350.0, 50.0], conf=0.99),
            OCRToken(text=f"ISSUED BY: {issuer}", bbox=[50.0, 60.0, 300.0, 85.0], conf=0.96),
            OCRToken(text=f"DATE: {issue_date}", bbox=[50.0, 95.0, 200.0, 115.0], conf=0.97),
        ]
        fields = {
            "title": ExtractedField(value=title, conf=1.0, bbox=[50.0, 20.0, 350.0, 50.0]),
            "issuer": ExtractedField(value=issuer, conf=1.0, bbox=[50.0, 60.0, 300.0, 85.0]),
            "date": ExtractedField(value=issue_date, conf=1.0, bbox=[50.0, 95.0, 200.0, 115.0]),
        }
        doc = DocumentResult(
            doc_id=doc_id,
            filename=filename,
            doc_type=doc_type,
            doc_type_conf=0.96,
            ocr=ocr_tokens,
            fields=fields,
            tables=[],
            validation=[],
            needs_review=False,
        )
        save_label(doc, out_path / f"{doc_id}.json")
        documents.append(doc)

    return documents


if __name__ == "__main__":
    docs = build_standard_30_test_set("data/labels")
    print(f"Successfully generated {len(docs)} benchmark label files in data/labels/")
