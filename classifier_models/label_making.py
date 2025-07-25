import os
import json
import random

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ #
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ #

# Create labels for text data
labels = {}
for category in ["legal", "literary", "technical"]:
    folder = os.path.join("train_files_txt", category)
    for file in os.listdir(folder):
        if file.endswith(".txt"):
            key = f"{category}/{file}"
            labels[key] = ["legal", "literary", "technical"].index(category)

keys = list(labels.keys())
random.shuffle(keys)

# Create new dictionary with shuffled order
shuffled_labels = {}
for key in keys:
    shuffled_labels[key] = labels[key]
    
with open("labels_txt.json", "w") as f:
    json.dump(shuffled_labels, f, indent=2)
