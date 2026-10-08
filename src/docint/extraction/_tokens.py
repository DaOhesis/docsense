"""
Token Normalization Module

Converts raw OCR token dictionaries into standardized OCRWord objects
to ensure consistent data access across the extraction pipeline.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class OCRWord:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float = 100.0  # stored 0-100 internally for convenience

    @property
    def x_center(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def y_center(self) -> float:
        return (self.y0 + self.y1) / 2


def tokens_to_words(tokens: List[Dict[str, Any]]) -> List[OCRWord]:
    """Convert contract-format OCRToken dicts into OCRWord objects."""
    words = []
    for t in tokens:
        x0, y0, x1, y1 = t["bbox"]
        conf_0_1 = t.get("conf", 1.0)
        words.append(OCRWord(text=t["text"], x0=x0, y0=y0, x1=x1, y1=y1, conf=conf_0_1 * 100.0))
    return words
