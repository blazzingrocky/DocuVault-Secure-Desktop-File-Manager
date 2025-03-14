from file_auto import FileAutomationSystem
import os

# Add this before initialization
print("Verifying training files:")
for category in ["legal", "literary", "technical"]:
    folder = os.path.join(r"C:\Users\shara\OneDrive - iitkgp.ac.in\IIT DOCS\Second Year\4th Sem\Software Eng Lab\Project\new train", category)
    if not os.path.exists(folder):
        print(f"⚠️ Missing folder: {folder}")
    else:
        print(f"✓ Found {len(os.listdir(folder))} files in {folder}")

# file_system = FileAutomationSystem(os.getcwd())
file_system = FileAutomationSystem(os.getcwd(), r"C:\Users\shara\OneDrive - iitkgp.ac.in\IIT DOCS\Second Year\4th Sem\Software Eng Lab\Project\new train")
