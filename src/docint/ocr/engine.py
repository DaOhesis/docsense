"""OWNER: Person A  |  Branch prefix: feature/ocr-*"""

import numpy as np
from paddleocr import PaddleOCR

from docint.schemas import OCRToken


# Initialize PaddleOCR once when the module is loaded.
ocr = PaddleOCR(
    lang="en",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)


def run_ocr(image: np.ndarray) -> list[OCRToken]:
    """Run PaddleOCR and return OCR tokens with bounding boxes and confidence."""

    # PaddleOCR 3.x accepts an image array as input.
    results = ocr.predict(image)

    tokens: list[OCRToken] = []

    for result in results:
        rec_texts = result["rec_texts"]
        rec_scores = result["rec_scores"]
        rec_boxes = result["rec_boxes"]

        for i in range(len(rec_texts)):
            token = OCRToken(
                text=rec_texts[i],
                bbox=rec_boxes[i].tolist(),
                conf=float(rec_scores[i])
            )

            tokens.append(token)

    return tokens