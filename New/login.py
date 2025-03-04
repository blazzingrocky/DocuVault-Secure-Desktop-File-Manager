import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk 
from filemanager import FileManagerGUI

class LoginPage(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Login Page")


        tk.Label(self, text="Username:").pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()


        tk.Label(self, text="Password:").pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()


        tk.Button(self, text="Login", command=self.login_submit).pack()
        tk.Button(self, text="Register", command=self.register_user).pack()
##############################################################################################################

    def login_submit(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        login_result = login_user(username, password)


        if login_result is None:
            messagebox.showinfo("Login Failed", "No user found with this username. Please register first.")
        elif login_result:
            self.destroy()
            app = FileManagerGUI()
            app.run()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")


    def register_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()


        # Ask if the user wants to set up automation during registration
        setup_automation = messagebox.askyesno(
            "Automation Setup", "Do you want to set up automation?")


        if setup_automation:
            # Prompt for the automation folder path
            automation_folder = filedialog.askdirectory(
                title="Select Automation Folder")
            if automation_folder:
                # Register the user and set up automation
                register_user(username, password, automation_folder)
            else:
                messagebox.showinfo(
                    "Registration", "Registration cancelled, no automation folder selected.")
        else:
            # Register the user without automation
            register_user(username, password, None)
def login_user(username, password):
    conn = sqlite3.connect('docuvault.db')
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        return None  # Username not found
    if bcrypt.checkpw(password.encode('utf-8'), result[0]):
        return True
    else:
        return False
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
