import subprocess
import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to your main.py (using os.path.join for proper path handling)
main_script = os.path.join(script_dir, "main.py")

# Run the main script without showing console window
subprocess.run(["pythonw", main_script], creationflags=subprocess.CREATE_NO_WINDOW)