import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk  # For the Treeview widget


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