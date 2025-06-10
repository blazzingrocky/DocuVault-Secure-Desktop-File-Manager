import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk  # For the Treeview widget
from login import LoginPage
from database import create_database

# --- Main Execution ---

# Set application ID for Windows taskbar icon
if os.name == 'nt':  # Windows
    try:
        import ctypes
        # This AppUserModelID helps Windows identify the application in the taskbar
        app_id = 'docuvault.filemanager.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

# --- Main Execution ---

if __name__ == "__main__":
    create_database()  # Ensure database is created before running the app
    login_app = LoginPage()  # Start with the login page
    login_app.iconbitmap("AppIcon\\DocuVault-icon.ico")  # Set the app icon
    login_app.mainloop()  # Run the login application loop
