"""OWNER: Person A  |  Branch prefix: feature/ocr-*

TODO:
  - wrap Tesseract and PaddleOCR behind the same interface
  - benchmark both on data/samples and record results in docs/ocr_benchmark.md
"""
import numpy as np

from docint.schemas import OCRToken


def run_ocr(image: np.ndarray) -> list[OCRToken]:
    """Return tokens with bounding boxes + confidence. STUB: returns dummy tokens."""
    return [
        OCRToken(text="INVOICE", bbox=[10, 10, 120, 40], conf=0.98),
        OCRToken(text="INV-1024", bbox=[10, 50, 120, 80], conf=0.95),
        OCRToken(text="Total: 1180.00", bbox=[10, 300, 200, 330], conf=0.93),
    ]
