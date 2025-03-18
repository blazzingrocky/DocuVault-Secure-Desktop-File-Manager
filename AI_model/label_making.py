import os
import json

# Create labels for image data
labels = {}
for category in ["buildings", "food", "human", "nature", "tech"]:
    folder = os.path.join("train_files_img", category)
    for file in os.listdir(folder):
        if file.endswith(".png") or file.endswith(".jpg"):
            key = f"{category}/{file}"
            labels[key] = ["buildings", "food", "human", "nature", "tech"].index(category)

with open("labels_img.json", "w") as f:
    json.dump(labels, f, indent=2)

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

with open("labels_txt.json", "w") as f:
    json.dump(labels, f, indent=2)
