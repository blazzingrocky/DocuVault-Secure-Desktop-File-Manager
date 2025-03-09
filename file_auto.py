import os
import shutil
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
from datetime import datetime
import json

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

        with open(file_path, 'r') as file:
            content = file.read()

        inputs = self.tokenizer(content, return_tensors="pt", max_length=512, truncation=True)
        inputs = {k: v.squeeze() for k, v in inputs.items()}

        return inputs, torch.tensor(label)

class FileAutomationSystem:
    def __init__(self, root_directory, train_folder="train_files", num_labels=3):
        self.root_directory = root_directory
        self.train_folder = train_folder
        self.extension_folders = {
            "pdf": os.path.join(root_directory, "pdf"),
            "jpg": os.path.join(root_directory, "image"),
            "txt": os.path.join(root_directory, "txt"),
            "docx": os.path.join(root_directory, "txt"),
            "c" : os.path.join(root_directory, "code"),
            "py" : os.path.join(root_directory, "code"),
            "java" : os.path.join(root_directory, "code"),
            "cpp" : os.path.join(root_directory, "code"),
            "html" : os.path.join(root_directory, "code")
            # Add more extensions as needed
        }
        self.subfolders = {
            "pdf": ["Novels", "Textbooks", "Datasheets"],
            "image": ["Landscapes", "Portraits", "Abstract"],
            "txt": ["Legal", "Technical", "Literary"],
            "code": ["Python", "Java", "C/C++", "HTML"]
            # Add more subfolders as needed
        }
        self.model_name = "bert-base-uncased"
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name, num_labels=num_labels)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # Load labels from JSON
        with open('labels.json') as f:
            self.labels_dict = json.load(f)
        
        # Prepare dataset and data loader
        self.file_paths = [os.path.join(self.train_folder, file) for file in self.labels_dict.keys()]
        self.labels = list(self.labels_dict.values())
        self.dataset = FileDataset(self.file_paths, self.labels, self.tokenizer)
        self.data_loader = torch.utils.data.DataLoader(self.dataset, batch_size=16, shuffle=True)
        
        # Fine-tune the model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-5)
        self.fine_tune_model()
        
    def fine_tune_model(self, epochs=5):
        for epoch in range(epochs):
            self.model.train()
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
            
            print(f"Epoch {epoch+1}, Loss: {total_loss / len(self.data_loader)}")
        
        self.model.eval()
    
    def create_extension_folders(self):
        for folder in self.extension_folders.values():
            if not os.path.exists(folder):
                os.makedirs(folder)
    
    def create_subfolders(self):
        for extension, subfolder_list in self.subfolders.items():
            extension_folder = self.extension_folders.get(extension.lower())
            if extension_folder:
                for subfolder in subfolder_list:
                    subfolder_path = os.path.join(extension_folder, subfolder)
                    if not os.path.exists(subfolder_path):
                        os.makedirs(subfolder_path)
    
    def get_file_extension(self, file_path):
        return os.path.splitext(file_path)[1][1:]
    
    def analyze_file_content(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read()
        
        inputs = self.tokenizer(content, return_tensors="pt", max_length=512, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        outputs = self.model(**inputs)
        category = torch.argmax(outputs.logits).item()
        
        return category
    
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