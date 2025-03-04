import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk
class AutomationWindow(tk.Toplevel):

    def __init__(self, parent, automation_folder):
        super().__init__(parent)
        self.title("Automation Window")
        self.geometry("400x300")
        self.automation_folder = automation_folder
        self.parent = parent  # Store a reference to the parent (FileManagerGUI)


        # Button to go back to file manager
        self.file_manager_button = tk.Button(
            self, text="Go to File Manager", command=self.go_to_file_manager)
        self.file_manager_button.pack()


        if not self.automation_folder:
            # Automation folder not set
            self.not_set_label = tk.Label(
                self, text="Automation folder not set.")
            self.not_set_label.pack()
            self.set_folder_button = tk.Button(
                self, text="Set Folder", command=self.set_automation_folder)
            self.set_folder_button.pack()
        else:
            # Automation folder is set
            self.folder_label = tk.Label(
                self, text=f"Automation Folder: {self.automation_folder}")
            self.folder_label.pack()
            self.open_folder_button = tk.Button(
                self, text="Open Folder", command=self.open_automation_folder)
            self.open_folder_button.pack()


    def go_to_file_manager(self):
        self.destroy()


    def set_automation_folder(self):
        folder_selected = filedialog.askdirectory(
            title="Select Automation Folder")
        if folder_selected:
            # Update the automation folder in the database
            self.update_automation_folder_db(folder_selected)


            # Update automation folder in file manager
            self.parent.automation_folder = folder_selected
            self.automation_folder = folder_selected  # Update local value


            # Destroy the current widgets
            self.not_set_label.destroy()
            self.set_folder_button.destroy()


            # Create labels and the button to open the folder
            self.folder_label = tk.Label(
                self, text=f"Automation Folder: {self.automation_folder}")
            self.folder_label.pack()
            self.open_folder_button = tk.Button(
                self, text="Open Folder", command=self.open_automation_folder)
            self.open_folder_button.pack()


    def open_automation_folder(self):
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.automation_folder)
            elif os.name == 'posix':  # macOS or Linux
                subprocess.Popen(['open', self.automation_folder])  # For macOS
            else:
                subprocess.Popen(['xdg-open', self.automation_folder])  # For Linux
        except OSError:
            messagebox.showerror("Error", "Could not open folder.")


    def update_automation_folder_db(self, automation_folder):
        """Updates the automation folder in the database."""
        conn = sqlite3.connect('docuvault.db')
        cursor = conn.cursor()
        try:
            # Update the user's automation folder in the database
            cursor.execute('UPDATE users SET automation_folder = ? WHERE username = ?',
                           (automation_folder, self.parent.username))
            conn.commit()
        except Exception as e:
            messagebox.showerror(
                "Error", f"Could not update automation folder in the database: {e}")
        finally:
            conn.close()



       
# --- Database Functions ---
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




def register_user(username, password, automation_folder):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = sqlite3.connect('docuvault.db')
    cursor = conn.cursor()
    try:
        if automation_folder:
            cursor.execute('INSERT INTO users (username, password, automation_folder) VALUES (?, ?, ?)',
                           (username, hashed, automation_folder))
        else:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                           (username, hashed))
        conn.commit()
        messagebox.showinfo("Registration", "User registered successfully!")
    except sqlite3.IntegrityError:
        messagebox.showerror("Registration Error", "Username already exists.")
    finally:
        conn.close()
