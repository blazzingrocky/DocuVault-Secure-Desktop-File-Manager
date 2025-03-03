import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
import time

# For SQLite
import sqlite3
import bcrypt

# For in-built text editor
import subprocess

def create_database():
    conn = sqlite3.connect('docuvault.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def register_user(username, password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = sqlite3.connect('docuvault.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
        conn.commit()
        messagebox.showinfo("Registration", "User registered successfully!")
    except sqlite3.IntegrityError:
        messagebox.showerror("Registration Error", "Username already exists.")
    
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


class LoginPage(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Login Page")
        
        # Username Label and Entry
        tk.Label(self, text="Username:").pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        # Password Label and Entry
        tk.Label(self, text="Password:").pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        # Login Button
        tk.Button(self, text="Login", command=self.login_submit).pack()

        # Register Button
        tk.Button(self, text="Register", command=self.register_user).pack()

    def login_submit(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        login_result = login_user(username, password)
        
        if login_result is None:
            messagebox.showinfo("Login Failed", "No user found with this username. Please register first.")
        elif login_result:
            self.destroy()  # Close login window if successful
            app = FileManagerGUI()  # Start the file manager application
            app.run()  # Run the application
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")


    def register_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        register_user(username, password)



class FileManagerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DocuVault: Secure Desktop File Manager")
        self.root.geometry("600x400")
        self.bin_dir = "c/Users/jbsch/OneDrive/Desktop/DocuVault/SWE_bin"

        # Ask user for directory choice
        choice = messagebox.askyesno("Directory Choice", "Do you want to start in the current directory?")
        if choice:
            self.current_dir = os.getcwd()
        else:
            # Use Desktop as the predefined root
            # self.current_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
            self.current_dir = "c/Users/jbsch/OneDrive/Desktop"

        # self.current_dir = os.getcwd()

        self.create_widgets()
        self.update_file_list()

    def create_widgets(self):
        # Path label
        self.path_label = tk.Label(self.root, text=self.current_dir)
        self.path_label.pack()

        # File listbox
        self.file_listbox = tk.Listbox(self.root, selectmode=tk.SINGLE)
        self.file_listbox.pack(expand=True, fill=tk.BOTH)
        self.file_listbox.bind("<Double-Button-1>", self.on_double_click)

        # Buttons frame
        self.buttons_frame = tk.Frame(self.root)
        self.buttons_frame.pack()

        # Create buttons
        buttons = [
            ("Create File", self.create_file),
            ("Create Folder", self.create_folder),
            ("Delete", self.delete_item),
            ("Move", self.move_item),
            ("Copy", self.copy_item),
            ("Go Back", self.go_to_parent_directory),
            ("Go to Bin", self.go_to_bin),  # Button for going to Bin
            ("Restore", self.restore_item)   # Button for restoring items from Bin
        ]

        for text, command in buttons:
            button = tk.Button(self.buttons_frame, text=text, command=command)
            button.pack(side=tk.LEFT)

        # bin_button = tk.Button(self.buttons_frame, text="Go to Bin", command=self.go_to_bin)
        # bin_button.pack(side=tk.LEFT)

    def go_to_bin(self):
        self.current_dir = self.bin_dir
        self.path_label.config(text=self.current_dir)
        self.update_file_list()

    def restore_item(self):
        selection = self.file_listbox.curselection()
        if selection:
            item = self.file_listbox.get(selection[0])
            item_path = os.path.join(self.bin_dir, item)

            dest = filedialog.askdirectory(title="Select Destination Folder")
            if dest:
                restored_path = os.path.join(dest, item)
                shutil.move(item_path, restored_path)
                # Navigate to the destination folder after restoring
                self.current_dir = dest
                self.path_label.config(text=self.current_dir)
                self.update_file_list()

    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for item in os.listdir(self.current_dir):
            self.file_listbox.insert(tk.END, item)

    def on_double_click(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            item = self.file_listbox.get(selection[0])
            item_path = os.path.join(self.current_dir, item)
            if os.path.isfile(item_path):
                # Check if the file is a text-based file
                text_extensions = ['.txt', '.py', '.html', '.css', '.js', '.md']  # Add more if needed
                file_extension = os.path.splitext(item_path)[1].lower()

                if file_extension in text_extensions:
                # Open the file in a text editor in read-only mode
                    try:
                        if os.name == 'nt':  # Windows
                            subprocess.Popen(['notepad.exe', item_path])  # Use notepad
                        elif os.name == 'posix':  # Linux/macOS
                            subprocess.Popen(['xdg-open', item_path])  # Use default text editor
                    except FileNotFoundError:
                        messagebox.showerror("Error", "Text editor not found.")

                else:
                    # Open the file with the default application
                    try:
                        if os.name == 'nt':  # Windows
                            os.startfile(item_path)
                        elif os.name == 'posix':  # Linux/macOS
                            subprocess.Popen(['xdg-open', item_path])
                    except OSError:
                        messagebox.showerror("Error", "Cannot open this file type.")
            elif os.path.isdir(item_path):
                self.current_dir = item_path
                self.path_label.config(text=self.current_dir)
                self.update_file_list()

    def create_file(self):
        filename = tk.simpledialog.askstring("Create File", "Enter file name:")
        if filename:
            with open(os.path.join(self.current_dir, filename), 'w') as f:
                pass
            self.update_file_list()

    def create_folder(self):
        foldername = tk.simpledialog.askstring("Create Folder", "Enter folder name:")
        if foldername:
            os.makedirs(os.path.join(self.current_dir, foldername), exist_ok=True)
            self.update_file_list()

    def auto_delete_from_bin(self):
        now = time.time()
        for filename in os.listdir(self.bin_dir):
            file_path = os.path.join(self.bin_dir, filename)
            if os.path.isfile(file_path):
                # Check last modified time
                if now - os.path.getmtime(file_path) > 30 * 86400:  # 30 days in seconds
                    os.remove(file_path)


    def delete_item(self):
        selection = self.file_listbox.curselection()
        if selection:
            item = self.file_listbox.get(selection[0])
            item_path = os.path.join(self.current_dir, item)
        
            # Ask for confirmation
            confirm = messagebox.askyesno("Confirm Delete", "Do you want to delete this item permanently?")
            if confirm:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            else:
                # Move to Bin
                shutil.move(item_path, self.bin_dir)
        
            self.update_file_list()


    def restore_item(self):
        selection = self.file_listbox.curselection()
        if selection:
            item = self.file_listbox.get(selection[0])
            item_path = os.path.join(self.bin_dir, item)
        
            dest = filedialog.askdirectory(title="Select Destination Folder")
            if dest:
                shutil.move(item_path, dest)
                self.update_file_list()



    def move_item(self):
        selection = self.file_listbox.curselection()
        if selection:
            item = self.file_listbox.get(selection[0])
            source = os.path.join(self.current_dir, item)
            dest = filedialog.askdirectory(title="Select Destination Folder")
            if dest:
                shutil.move(source, dest)
                self.update_file_list()

    def copy_item(self):
        selection = self.file_listbox.curselection()
        if selection:
            item = self.file_listbox.get(selection[0])
            source = os.path.join(self.current_dir, item)
            dest = filedialog.askdirectory(title="Select Destination Folder")
            if dest:
                if os.path.isfile(source):
                    shutil.copy2(source, dest)
                elif os.path.isdir(source):
                    shutil.copytree(source, os.path.join(dest, item))
                self.update_file_list()

    def go_to_parent_directory(self):
        self.current_dir = os.path.dirname(self.current_dir)
        self.path_label.config(text=self.current_dir)
        self.update_file_list()

    def run(self):
       """Run the Tkinter main loop."""
       self.root.mainloop()


if __name__ == "__main__":
    create_database()  # Ensure database is created before running the app
    login_app = LoginPage()  # Start with the login page
    login_app.mainloop()  # Run the login application loop
