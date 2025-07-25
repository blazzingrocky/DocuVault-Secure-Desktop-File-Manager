import os
import torch
import json
from sklearn.metrics import accuracy_score, classification_report
from transformers import AutoModelForSequenceClassification, AutoTokenizer

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# Test Text Classification Model
def test_text_model(model_path, test_folder, labels_json_path):
    print("Testing Text Classification Model...")
    
    # Device setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load the model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.to(device)
    model.eval()
    
    # Load labels dictionary
    with open(labels_json_path, 'r') as f:
        labels_dict = json.load(f)
    
    # Prepare test data
    all_preds = []
    all_labels = []
    file_paths = []
    
    for rel_path, label in labels_dict.items():
        file_path = os.path.join(test_folder, rel_path)
        if os.path.exists(file_path):
            file_paths.append(file_path)
            all_labels.append(label)
    
    # Run predictions
    cnt = 0
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
        
        inputs = tokenizer(
            content,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding="max_length"
        ).to(device)
        
        with torch.no_grad():
            outputs = model(**inputs)
            pred = torch.argmax(outputs.logits).item()
        cnt += 1
        all_preds.append(pred)

        if cnt == 100:
            break
    
    # Calculate metrics
    accuracy = accuracy_score(all_labels[0:100], all_preds)
    report = classification_report(all_labels[0:100], all_preds, zero_division=0)
    
    print(f"Text Classification Accuracy: {accuracy:.4f}")
    print("Classification Report:")
    print(report)
    
    return accuracy, report

if __name__ == "__main__":
    # Test text classification model
    text_model_path = "saved_model_txt"  # Path to saved text model
    test_folder = r"C:\Users\jbsch\OneDrive\Desktop\train_files_txt"  # Folder with test text files
    labels_json_path = "labels_txt.json"  # Path to labels json
    
    accuracy, report = test_text_model(text_model_path, test_folder, labels_json_path)
    
    print("\nSummary:")
    print(f"Text Classification Accuracy: {accuracy:.4f}")
