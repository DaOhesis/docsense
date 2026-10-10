from pathlib import Path
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from docint.schemas import DocType, OCRToken

DEFAULT_TRAINING_DATA = [
    ("invoice number bill to subtotal tax due date balance", DocType.invoice.value),
    ("tax invoice quantity unit price total amount payable", DocType.invoice.value),
    ("receipt cashier change due thank you for shopping total paid", DocType.receipt.value),
    ("pos receipt order summary visa mastercard tip total", DocType.receipt.value),
    ("certificate of completion awarded to hereby certify signature date", DocType.certificate.value),
    ("achievement certificate presented to authorized signatory", DocType.certificate.value),
    ("application form full name date of birth applicant signature please print", DocType.form.value),
    ("registration form check one box office use only", DocType.form.value),
]


class MLDocumentClassifier:
    def __init__(self, confidence_threshold: float = 0.40):
        self.confidence_threshold = confidence_threshold
        self.model = Pipeline([
            ("tfidf", TfidfVectorizer(lowercase=True)),
            ("clf", LogisticRegression(C=10.0))
        ])
        self.is_trained = False

    def train(self, texts: list[str], labels: list[str]) -> None:
        """Trains the TF-IDF + Logistic Regression pipeline on labeled text."""
        self.model.fit(texts, labels)
        self.is_trained = True

    def save(self, filepath: str | Path) -> None:
        """Saves the trained Scikit-learn pipeline to disk."""
        if not self.is_trained:
            raise ValueError("Cannot save an untrained model.")
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)

    def load(self, filepath: str | Path) -> None:
        """Loads a pre-trained Scikit-learn pipeline from disk."""
        self.model = joblib.load(filepath)
        self.is_trained = True

    def classify(self, tokens: list[OCRToken]) -> tuple[DocType, float]:
        """
        Takes OCRTokens and returns (DocType, calculated_probability)
        strictly following the schemas.py data contract.
        """
        if not tokens:
            return DocType.unknown, 0.0

        if not self.is_trained:
            texts, labels = zip(*DEFAULT_TRAINING_DATA)
            self.train(list(texts), list(labels))

        full_text = " ".join([t.text for t in tokens])

        probabilities = self.model.predict_proba([full_text])[0]
        max_index = int(np.argmax(probabilities))
        best_confidence = float(probabilities[max_index])
        best_label = self.model.classes_[max_index]

        if best_confidence < self.confidence_threshold:
            return DocType.unknown, round(best_confidence, 4)

        return DocType(best_label), round(best_confidence, 4)


_default_classifier = MLDocumentClassifier()

def classify_ml(tokens: list[OCRToken]) -> tuple[DocType, float]:
    return _default_classifier.classify(tokens)