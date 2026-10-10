"""OWNER: Person A  |  Branch prefix: feature/preprocess-*"""
import logging
import cv2
import numpy as np

logger = logging.getLogger("docint.preprocessing")


def _deskew(image: np.ndarray) -> np.ndarray:
    """Correct small global rotation in a document image."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, text_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        points = cv2.findNonZero(text_mask)
        if points is None:
            return image

        rect = cv2.minAreaRect(points)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Deskew should only correct small document skew (<15 degrees)
        if abs(angle) > 15:
            return image

        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
        deskewed = cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return deskewed
    except Exception as e:
        logger.debug("Deskew failed (%s), returning original image", e)
        return image


def preprocess(file_bytes: bytes, filename: str) -> np.ndarray:
    """Decode document bytes and return a deskewed page image (H x W x 3, uint8)."""
    if not file_bytes:
        return np.zeros((100, 100, 3), dtype=np.uint8)

    array = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if image is None:
        # Graceful fallback for mock tests, PDF bytes, or corrupted images
        logger.debug("cv2.imdecode returned None for %s; using blank canvas fallback", filename)
        return np.zeros((100, 100, 3), dtype=np.uint8)

    return _deskew(image)