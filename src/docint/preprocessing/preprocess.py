"""OWNER: Person A  |  Branch prefix: feature/preprocess-*

TODO:
  - decode image / PDF pages (cv2.imdecode, PyMuPDF or pdf2image)
  - deskew, denoise, adaptive threshold, contrast enhancement
  - keep it deterministic and fast
"""
import numpy as np


def preprocess(file_bytes: bytes, filename: str) -> np.ndarray:
    """Return a cleaned-up page image (H x W x 3, uint8). STUB: returns a blank image."""
    return np.zeros((100, 100, 3), dtype=np.uint8)
