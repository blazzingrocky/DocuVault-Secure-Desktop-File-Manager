import os
import shutil
import json
import torch
from datetime import datetime
from transformers import AutoModelForSequenceClassification, AutoTokenizer

class FileDataset(torch.utils.data.Dataset):
    def __init__(self, file_paths, labels, tokenizer):
        self.file_paths = file_paths
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        file_path = self.file_paths[idx]
        label = self.labels[idx]
        # Fix encoding and error handling
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
        inputs = self.tokenizer(
            content, 
            return_tensors="pt", 
            max_length=512, 
            truncation=True,
            padding="max_length" # Pad to max length
        )
        return {k: v.squeeze() for k, v in inputs.items()}, torch.tensor(label)

class FileAutomationSystem:
    def __init__(self, root_directory, train_folder="train_files", num_labels=3):
        self.root_directory = root_directory
        self.train_folder = train_folder
        
        # Load category mapping from labels.json
        with open('labels.json') as f:
            self.labels_dict = json.load(f)
        
        # Initialize model and tokenizer
        self.model_name = "bert-base-uncased"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=num_labels,
            ignore_mismatched_sizes=True  # Handle dimension mismatches
        )
        
        # Prepare training data
        self.file_paths = [
            os.path.normpath(os.path.join(self.train_folder, rel_path))
            for rel_path in self.labels_dict.keys()
        ]

        # Add file existence check
        for fp in self.file_paths:
            if not os.path.exists(fp):
                raise FileNotFoundError(f"Training file missing: {fp}")
            
        self.labels = list(self.labels_dict.values())
        
        # Create dataset and dataloader
        self.dataset = FileDataset(self.file_paths, self.labels, self.tokenizer)
        self.data_loader = torch.utils.data.DataLoader(
            self.dataset, 
            batch_size=8, 
            shuffle=True
        )
        
        # Fine-tune model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=2e-5)
        self.fine_tune_model(epochs=3)

    def fine_tune_model(self, epochs=3):
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch in self.data_loader:
                inputs, labels = batch
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                labels = labels.to(self.device)
                
                self.optimizer.zero_grad()
                outputs = self.model(**inputs, labels=labels)
                loss = outputs.loss
                loss.backward()
                self.optimizer.step()
                
                total_loss += loss.item()
            
            print(f"Epoch {epoch+1} Loss: {total_loss/len(self.data_loader):.4f}")

    def analyze_file_content(self, file_path):
        self.model.eval()
        with open(file_path, 'r') as file:
            content = file.read()
        
        inputs = self.tokenizer(
            content,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding="max_length"
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        return torch.argmax(outputs.logits).item()
    
    def move_to_subfolder(self, file_path):
        subfolder_name = self.get_subfolder_name(self.analyze_file_content(file_path))
        extension = self.get_file_extension(file_path)
        extension_folder = self.extension_folders.get(extension)
        
        if extension_folder:
            subfolder_path = os.path.join(extension_folder, subfolder_name)
            shutil.move(file_path, subfolder_path)
    
    def get_subfolder_name(self, category):
        # Example mapping for PDFs
        if category == 0:
            return "Novels"
        elif category == 1:
            return "Textbooks"
        # Add more mappings as needed
    
    def extract_metadata(self, file_path):
        metadata = {
            "filename": os.path.basename(file_path),
            "modified_date": datetime.fromtimestamp(os.path.getmtime(file_path)),
            "size": os.path.getsize(file_path),
        }
        return metadata
    
    def smart_search(self, query):
        results = []
        for root, dirs, files in os.walk(self.root_directory):
            for file in files:
                file_path = os.path.join(root, file)
                if query.lower() in file.lower():
                    results.append(file_path)
        return results

    def anomaly_detection(self):
        # Example anomaly detection implementation
        # Monitor file access patterns and flag unusual activity
        pass

    def automated_backup(self):
        # Example automated backup implementation
        # Prioritize frequently accessed files for backup
        pass

    def collaborative_annotations(self):
        # Example collaborative annotations implementation
        # Integrate permissions so shared files maintain strict access rules
        pass

    def visual_file_management(self):
        # Example visual file management implementation
        # Present a dashboard with statistics like file type distribution
        pass