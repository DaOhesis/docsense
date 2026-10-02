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

from docint.classifier.ml_classifier import classify_ml

def test_ml_classifier_invoice():
    mock_tokens = [
        OCRToken(text="Bill", bbox=[0, 0, 10, 10], conf=0.99),
        OCRToken(text="To:", bbox=[12, 0, 20, 10], conf=0.99),
        OCRToken(text="Subtotal", bbox=[0, 50, 40, 60], conf=0.99),
        OCRToken(text="Tax", bbox=[0, 70, 30, 80], conf=0.99),
    ]
    
    doc_type, confidence = classify_ml(mock_tokens)
    
    assert doc_type == DocType.invoice
    assert 0.40 <= confidence <= 1.0

from docint.classifier.layout_analyzer import detect_key_value_pairs, detect_table_rows
from docint.classifier.ml_classifier import MLDocumentClassifier

def test_layout_kv_and_tables():
    mock_tokens = [
        # Key-Value pair on line y=100
        OCRToken(text="Date:", bbox=[10, 100, 50, 115], conf=0.99),
        OCRToken(text="2026-10-02", bbox=[60, 100, 140, 115], conf=0.99),
        
        # Table row (3 columns) on line y=200
        OCRToken(text="ItemA", bbox=[10, 200, 60, 215], conf=0.99),
        OCRToken(text="2", bbox=[150, 200, 165, 215], conf=0.99),
        OCRToken(text="$20.00", bbox=[250, 200, 300, 215], conf=0.99),
    ]
    
    kv = detect_key_value_pairs(mock_tokens)
    tables = detect_table_rows(mock_tokens, min_columns=3)
    
    assert kv == {"Date": "2026-10-02"}
    assert len(tables) == 1
    assert tables[0] == ["ItemA", "2", "$20.00"]


def test_ml_save_and_load(tmp_path):
    clf = MLDocumentClassifier()
    # Trigger training and save to a temporary file
    token = [OCRToken(text="Invoice Subtotal Tax", bbox=[0, 0, 10, 10], conf=0.99)]
    clf.classify(token)
    
    model_file = tmp_path / "model.joblib"
    clf.save(model_file)
    
    # Load into a brand new classifier instance
    loaded_clf = MLDocumentClassifier()
    loaded_clf.load(model_file)
    doc_type, conf = loaded_clf.classify(token)
    
    assert doc_type == DocType.invoice
    assert conf >= 0.40