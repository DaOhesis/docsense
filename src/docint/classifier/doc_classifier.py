from docint.schemas import DocType, OCRToken

def classify(tokens: list[OCRToken]) -> tuple[DocType, float]:
    """
    A simple rule-based classifier. 
    It reads all the OCR text and looks for obvious keywords.
    """
    if not tokens:
        return DocType.unknown, 0.0
        
    full_text = " ".join([token.text.lower() for token in tokens])
    
    if "invoice" in full_text or "bill to" in full_text:
        return DocType.invoice, 0.8
        
    elif "receipt" in full_text or "total paid" in full_text:
        return DocType.receipt, 0.8
        
    elif "certificate" in full_text or "certify" in full_text:
        return DocType.certificate, 0.8
        
    elif "application" in full_text or "form" in full_text or "signature:" in full_text:
        return DocType.form, 0.6
        
    return DocType.unknown, 0.1
