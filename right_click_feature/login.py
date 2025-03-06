import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk  # For the Treeview widget
from database import create_database, register_user, login_user
from automation import AutomationWindow
from filemanager import FileManagerGUI

class LoginPage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Login Page")
        self.geometry("300x200")
        tk.Label(self, text="Username:").pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()
        tk.Label(self, text="Password:").pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()
        tk.Button(self, text="Login", command=self.login_submit).pack()
        tk.Button(self, text="Register", command=self.register_user).pack()

    def login_submit(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        login_result = login_user(username, password)
        if login_result is None:
            messagebox.showinfo("Login Failed", "No user found with this username. Please register first.")
        elif login_result:
            self.destroy()
            app = FileManagerGUI(username)
            app.run()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    def register_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        setup_automation = messagebox.askyesno("Automation Setup", "Do you want to set up automation?")
        if setup_automation:
            automation_folder = filedialog.askdirectory(title="Select Automation Folder")
            if automation_folder:
                register_user(username, password, automation_folder)
            else:
                messagebox.showinfo("Registration", "Registration cancelled, no automation folder selected.")
        else:
            register_user(username, password, None)