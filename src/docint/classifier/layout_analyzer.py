from docint.schemas import OCRToken

def detect_regions(tokens: list[OCRToken], page_height: float) -> dict:
    """
    Categorizes tokens into Header, Body, or Footer based on their Y-coordinates.
    """
    regions = {
        "header": [],
        "body": [],
        "footer": []
    }
    
    if not tokens:
        return regions

    header_threshold = page_height * 0.15
    footer_threshold = page_height * 0.85

    for token in tokens:
        x1, y1, x2, y2 = token.bbox
        
        if y2 <= header_threshold:
            regions["header"].append(token)
            
        elif y1 >= footer_threshold:
            regions["footer"].append(token)
            
        else:
            regions["body"].append(token)
            
    return regions