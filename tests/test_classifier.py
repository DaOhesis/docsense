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

from docint.classifier.layout_analyzer import detect_regions

def test_layout_regions():
    page_height = 1000.0
    
    mock_tokens = [
        OCRToken(text="INVOICE", bbox=[10, 50, 100, 100], conf=0.9),
        
        OCRToken(text="Total: $50", bbox=[10, 500, 150, 550], conf=0.9),
        
        OCRToken(text="Page 1 of 1", bbox=[10, 900, 100, 950], conf=0.9),
    ]
    
    regions = detect_regions(mock_tokens, page_height)
    
    assert len(regions["header"]) == 1
    assert regions["header"][0].text == "INVOICE"
    
    assert len(regions["body"]) == 1
    assert regions["body"][0].text == "Total: $50"
    
    assert len(regions["footer"]) == 1
    assert regions["footer"][0].text == "Page 1 of 1"