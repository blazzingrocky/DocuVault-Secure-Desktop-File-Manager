import os
import json

labels = {}
for category in ["legal", "literary", "technical"]:
    folder = os.path.join(r"C:\Users\shara\OneDrive - iitkgp.ac.in\IIT DOCS\Second Year\4th Sem\Software Eng Lab\Project\train_files\train_files", category)
    for file in os.listdir(folder):
        if file.endswith(".txt"):
            key = f"{category}/{file}"
            labels[key] = ["legal", "literary", "technical"].index(category)

with open("labels.json", "w") as f:
    json.dump(labels, f, indent=2)
