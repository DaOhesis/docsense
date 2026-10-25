"""OWNER: Person A  |  Branch prefix: feature/preprocess-*"""
import logging
import cv2
import numpy as np

logger = logging.getLogger("docint.preprocessing")


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _perspective_rectify(image: np.ndarray) -> np.ndarray:
    """Detect prominent quadrilateral document boundary in a phone photo and unwarp it."""
    try:
        h, w = image.shape[:2]
        total_area = h * w
        if total_area < 40000:
            return image

        scale = 800.0 / max(h, w)
        small = cv2.resize(image, (int(w * scale), int(h * scale)))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(approx) / (scale * scale)
                # Only rectify if the quad covers between 25% and 92% of the image
                if 0.25 * total_area <= area <= 0.92 * total_area:
                    pts = approx.reshape(4, 2) / scale
                    rect = _order_points(pts)
                    (tl, tr, br, bl) = rect

                    width_a = np.hypot(br[0] - bl[0], br[1] - bl[1])
                    width_b = np.hypot(tr[0] - tl[0], tr[1] - tl[1])
                    max_width = max(int(width_a), int(width_b))

                    height_a = np.hypot(tr[0] - br[0], tr[1] - br[1])
                    height_b = np.hypot(tl[0] - bl[0], tl[1] - bl[1])
                    max_height = max(int(height_a), int(height_b))

                    if max_width > 50 and max_height > 50:
                        dst = np.array([
                            [0, 0],
                            [max_width - 1, 0],
                            [max_width - 1, max_height - 1],
                            [0, max_height - 1]
                        ], dtype="float32")
                        matrix = cv2.getPerspectiveTransform(rect, dst)
                        warped = cv2.warpPerspective(image, matrix, (max_width, max_height))
                        return warped
    except Exception as e:
        logger.debug("Perspective rectification skipped: %s", e)
    return image


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


def enhance_image(image: np.ndarray) -> np.ndarray:
    """Enhance document contrast and denoise for improved OCR accuracy."""
    try:
        # Convert to LAB color space to equalize luminance channel (CLAHE)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return enhanced
    except Exception as e:
        logger.debug("Contrast enhancement failed: %s", e)
        return image


def _rasterize_pdf(file_bytes: bytes) -> np.ndarray | None:
    """Render the first page of a PDF file to a BGR numpy image at 200 DPI."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            img_data = pix.tobytes("png")
            return cv2.imdecode(np.frombuffer(img_data, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception as e:
        logger.debug("PyMuPDF PDF rasterization failed: %s", e)
    return None


def preprocess(file_bytes: bytes, filename: str, enhance: bool = True) -> np.ndarray:
    """Decode document bytes and return a deskewed, enhanced page image (H x W x 3, uint8)."""
    if not file_bytes:
        return np.zeros((100, 100, 3), dtype=np.uint8)

    image = None
    safe_fn = filename.lower()
    if safe_fn.endswith(".pdf") or file_bytes.startswith(b"%PDF"):
        image = _rasterize_pdf(file_bytes)

    if image is None:
        array = np.frombuffer(file_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if image is None:
        logger.debug("Image decoding returned None for %s; using blank canvas fallback", filename)
        return np.zeros((100, 100, 3), dtype=np.uint8)

    # 1. Perspective rectify (useful for camera-captured receipts/documents)
    rectified = _perspective_rectify(image)

    # 2. Deskew small rotational tilts
    deskewed = _deskew(rectified)

    # 3. Contrast enhancement
    if enhance:
        return enhance_image(deskewed)
    return deskewed