import os

try:
    from sklearn.metrics import classification_report, confusion_matrix
    _HAS_SKLEARN = True
except ImportError:
    classification_report = None
    confusion_matrix = None
    _HAS_SKLEARN = False

from docint.classifier.doc_classifier import classify_rules as classify_baseline
from docint.classifier.ml_classifier import classify_ml
from docint.schemas import OCRToken

# Realistic simulated OCR text that doesn't always include the obvious keyword
MOCK_REALISTIC_TEXT = {
    "invoice": ["Bill", "To:", "Subtotal", "Tax", "Balance", "Due"],
    "receipt": ["Cashier", "Thank", "You", "Change", "Due", "Visa"],
    "form": ["Full", "Name", "Date", "of", "Birth", "Check", "Box"],
    "certificate": ["Awarded", "to", "Authorized", "Signatory", "Completion"],
}

def mock_ocr(filepath: str) -> list[OCRToken]:
    """Simulates realistic contextual words found on each document type."""
    true_label = os.path.basename(os.path.dirname(filepath))
    words = MOCK_REALISTIC_TEXT.get(true_label, ["unknown"])
    return [OCRToken(text=w, bbox=[0, 0, 10, 10], conf=0.99) for w in words]


def run_evaluation():
    if not _HAS_SKLEARN:
        print("scikit-learn is required to run evaluation reports.")
        return

    samples_dir = "data/samples"
    valid_types = ["invoice", "receipt", "form", "certificate"]
    
    y_true = []
    y_pred_baseline = []
    y_pred_ml = []
    
    for doc_type in valid_types:
        folder_path = os.path.join(samples_dir, doc_type)
        if not os.path.exists(folder_path):
            continue
            
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            tokens = mock_ocr(filepath)
            
            base_type, _ = classify_baseline(tokens)
            ml_type, _ = classify_ml(tokens)
            
            y_true.append(doc_type)
            y_pred_baseline.append(base_type.value)
            y_pred_ml.append(ml_type.value)

    if not y_true:
        print("No samples found in data/samples subfolders!")
        return

    print("=== 1. KEYWORD BASELINE REPORT ===")
    print(classification_report(y_true, y_pred_baseline, zero_division=0))

    print("=== 2. TF-IDF + LOGISTIC REGRESSION (ML) REPORT ===")
    print(classification_report(y_true, y_pred_ml, zero_division=0))

    print("=== ML CONFUSION MATRIX ===")
    labels = sorted(list(set(y_true + y_pred_ml)))
    print(f"Labels: {labels}")
    print(confusion_matrix(y_true, y_pred_ml, labels=labels))


if __name__ == "__main__":
    run_evaluation()