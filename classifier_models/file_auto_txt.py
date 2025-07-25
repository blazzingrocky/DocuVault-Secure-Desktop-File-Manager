import os
import shutil
import json
import torch
from datetime import datetime
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from fastapi import FastAPI, File, UploadFile
import uvicorn
import random

class TextDataset(torch.utils.data.Dataset):
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

class TextClassifierSystem:
    def __init__(self, root_directory, train_folder="train_files_txt", num_labels=3):
        self.root_directory = root_directory
        self.train_folder = train_folder
        self.model_save_path = os.path.join(root_directory, "saved_model_txt")
        
        if os.path.exists(self.model_save_path):
            # Load existing model [1]
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_save_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_save_path,
                num_labels=num_labels,
                ignore_mismatched_sizes=True
            )
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            print("Loaded pre-trained model from", self.model_save_path)
        # Load category mapping from labels.json
        else:
            with open('labels_txt.json') as f:
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
            self.dataset = TextDataset(self.file_paths, self.labels, self.tokenizer)
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

            # Save model and tokenizer
            os.makedirs(self.model_save_path, exist_ok=True)
            self.model.save_pretrained(self.model_save_path)
            self.tokenizer.save_pretrained(self.model_save_path)
            print("Saved fine-tuned model to", self.model_save_path)

        self.app = FastAPI(title="Text Classification API")
        self.setup_routes()

    def setup_routes(self):
        @self.app.post("/predict_txt")
        async def predict(file: UploadFile = File(...)):
            content = await file.read()
            return await self.analyze_content(content.decode('utf-8'))

    async def analyze_content(self, content: str):
        inputs = self.tokenizer(
            content,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding="max_length"
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        return {"category": torch.argmax(outputs.logits).item()}

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

    def serve_model(self, host='0.0.0.0', port=8000):
        """Start FastAPI server with the trained model"""
        uvicorn.run(self.app, host=host, port=port)
 
    