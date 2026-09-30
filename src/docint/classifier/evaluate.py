import os
from docint.classifier.doc_classifier import classify
from docint.schemas import OCRToken

def mock_ocr(filepath: str) -> list[OCRToken]:
    true_label = os.path.basename(os.path.dirname(filepath))
    
    # Return a fake OCR token
    return [OCRToken(text=true_label, bbox=[0,0,10,10], conf=0.99)]


def run_evaluation():
    samples_dir = "data/samples"
    valid_types = ["invoice", "receipt", "form", "certificate"]
    
    correct = 0
    total = 0
    
    print("Starting Baseline Evaluation...\n" + "-"*30)
    
    for doc_type in valid_types:
        folder_path = os.path.join(samples_dir, doc_type)
        if not os.path.exists(folder_path):
            continue
            
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            total += 1
            
            tokens = mock_ocr(filepath)
            
            predicted_type, confidence = classify(tokens)
            
            if predicted_type.value == doc_type:
                correct += 1
                print(f"✅ {filename} -> {predicted_type.value} (Conf: {confidence})")
            else:
                print(f"❌ {filename} -> {predicted_type.value} (Expected: {doc_type})")
                
    if total > 0:
        accuracy = (correct / total) * 100
        print("-" * 30)
        print(f"Baseline Accuracy: {correct}/{total} ({accuracy:.1f}%)")
    else:
        print("No samples found. Did you put them in the subfolders?")

if __name__ == "__main__":
    run_evaluation()