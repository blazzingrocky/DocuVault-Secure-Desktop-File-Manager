import os
import json
import torch
from datetime import datetime
from torchvision import transforms
from torchvision.models import resnet50, ResNet50_Weights
from fastapi import FastAPI, File, UploadFile
import uvicorn
import io
from PIL import Image
import random

class ImageDataset(torch.utils.data.Dataset):
    def __init__(self, file_paths, labels, transform):
        self.file_paths = file_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        file_path = self.file_paths[idx]
        label = self.labels[idx]
        
        image = Image.open(file_path).convert('RGB')
        image = self.transform(image)
        
        return image, torch.tensor(label)

class ImageClassifierSystem:
    def __init__(self, root_directory, train_folder="train_files_img", num_labels=3):
        self.root_directory = root_directory
        self.train_folder = train_folder
        self.model_save_path = os.path.join(root_directory, "saved_model_img")
        
        # Image transformations
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                 std=[0.229, 0.224, 0.225])
        ])

        if os.path.exists(self.model_save_path):
            # Load existing model
            self.model = resnet50(weights=None)
            self.model.fc = torch.nn.Linear(self.model.fc.in_features, num_labels)
            self.model.load_state_dict(torch.load(os.path.join(self.model_save_path, "model.pth")))
            
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            print("Loaded pre-trained model from", self.model_save_path)
        else:
            # Initialize new model
            self.model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
            self.model.fc = torch.nn.Linear(self.model.fc.in_features, num_labels)
            
            # Load labels from JSON
            with open('labels_img.json') as f:
                self.labels_dict = json.load(f)

            # Prepare training data
            self.file_paths = [
                os.path.normpath(os.path.join(self.train_folder, rel_path))
                for rel_path in self.labels_dict.keys()
            ]
            self.labels = list(self.labels_dict.values())

            # Verify files exist
            for fp in self.file_paths:
                if not os.path.exists(fp):
                    raise FileNotFoundError(f"Training file missing: {fp}")

            # Create dataset and dataloader
            self.dataset = ImageDataset(self.file_paths, self.labels, self.transform)
            self.data_loader = torch.utils.data.DataLoader(
                self.dataset,
                batch_size=8,
                shuffle=True
            )

            # Training setup
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-4)
            self.criterion = torch.nn.CrossEntropyLoss()
            
            self.fine_tune_model(epochs=5)
            
            # Save model
            os.makedirs(self.model_save_path, exist_ok=True)
            torch.save(self.model.state_dict(), os.path.join(self.model_save_path, "model.pth"))
            print("Saved fine-tuned model to", self.model_save_path)

        self.app = FastAPI(title="Image Classification API")
        self.setup_routes()

    def setup_routes(self):
        @self.app.post("/predict_img")
        async def predict(file: UploadFile = File(...)):
            content = await file.read()
            return await self.analyze_image(content)

    async def analyze_image(self, image_bytes: bytes):
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        image = self.transform(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(image)
            _, predicted = torch.max(outputs, 1)
            
        return {"category": predicted.item()}

    def fine_tune_model(self, epochs=3):
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for images, labels in self.data_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                
                self.optimizer.zero_grad()
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()
                
                total_loss += loss.item()
            
            print(f"Epoch {epoch+1} Loss: {total_loss/len(self.data_loader):.4f}")

    def serve_model(self, host='0.0.0.0', port=8001):
        uvicorn.run(self.app, host=host, port=port)


