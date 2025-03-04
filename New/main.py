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
from filemanager import FileManagerGUI
from automation import AutomationWindow
def create_database():
    conn = sqlite3.connect('docuvault.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    automation_folder TEXT
    )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()  # Ensure database is created before running the app
    login_app = LoginPage()  # Start with the login page
    login_app.mainloop()  # Run the login application loop