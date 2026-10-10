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


def tokens_to_words(tokens: List[Any]) -> List[OCRWord]:
    """Convert contract-format OCRToken dicts or Pydantic models into OCRWord objects."""
    words = []
    for t in tokens:
        if isinstance(t, dict):
            bbox = t.get("bbox", [0.0, 0.0, 0.0, 0.0])
            text = t.get("text", "")
            conf_0_1 = t.get("conf", 1.0)
        else:
            bbox = getattr(t, "bbox", [0.0, 0.0, 0.0, 0.0])
            text = getattr(t, "text", "")
            conf_0_1 = getattr(t, "conf", 1.0)
        x0, y0, x1, y1 = bbox
        words.append(OCRWord(text=text, x0=x0, y0=y0, x1=x1, y1=y1, conf=conf_0_1 * 100.0))
    return words
