from model import ImageClassificationModel

# Initialize model
classification_model = ImageClassificationModel()
image_path = "Profile Pic.jpg"  # Replace with your image path

# Run inference
results = classification_model(image_path, num_classes=5)

# Print results
print("Top 5 predicted classes:")
for prob, label in results:
    print(f"{label}: {prob*100:.2f}%")
