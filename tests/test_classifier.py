from docint.schemas import DocType, OCRToken
from docint.classifier.doc_classifier import classify

def test_classify_invoice():
    # fake 'mock' tokens.
    mock_tokens = [
        OCRToken(text="Company", bbox=[10, 10, 50, 20], conf=0.99),
        OCRToken(text="INVOICE", bbox=[100, 10, 150, 20], conf=0.99),
        OCRToken(text="Total:", bbox=[10, 50, 40, 60], conf=0.99),
    ]
    
    doc_type, confidence = classify(mock_tokens)
    
    assert doc_type == DocType.invoice
    assert confidence == 0.8

def test_classify_unknown():
    mock_tokens = [
        OCRToken(text="Hello", bbox=[0,0,1,1], conf=0.9),
        OCRToken(text="World", bbox=[0,0,1,1], conf=0.9),
    ]
    doc_type, confidence = classify(mock_tokens)
    
    assert doc_type == DocType.unknown