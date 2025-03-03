import os
import shutil
import sqlite3
import bcrypt
import tkinter as tk
from tkinter import filedialog, messagebox

# Database setup
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
    
    if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
        conn.close()
        return True
    else:
        conn.close()
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
        
        if login_user(username, password):
            self.destroy()  # Close login window if successful
            app = FileManagerGUI()  # Start the file manager application
            app.run()  # Run the application

    def register_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        register_user(username, password)

class FileManagerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DocuVault: Secure Desktop File Manager")
        self.root.geometry("600x400")

        # Create Bin directory on Desktop
        self.bin_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'Bin')
        os.makedirs(self.bin_dir, exist_ok=True)

        # Set initial directory to Desktop
        self.current_dir = os.path.join(os.path.expanduser('~'), 'Desktop')

        self.create_widgets()
        self.update_file_list()

    def create_widgets(self):
        # Path label
        self.path_label = tk.Label(self.root, text=self.current_dir)
        self.path_label.pack()

        # File listbox
        self.file_listbox = tk.Listbox(self.root, selectmode=tk.SINGLE)
        self.file_listbox.pack(expand=True, fill=tk.BOTH)
        
        # Buttons frame
        self.buttons_frame = tk.Frame(self.root)
        self.buttons_frame.pack()

        # Create buttons for file operations and navigation
        buttons = [
            ("Create File", self.create_file),
            ("Create Folder", self.create_folder),
            ("Delete", self.delete_item),
            ("Move", self.move_item),
            ("Copy", self.copy_item),
            ("Go to Bin", self.go_to_bin),
            ("Restore", self.restore_item)
        ]

        for text, command in buttons:
            button = tk.Button(self.buttons_frame, text=text, command=command)
            button.pack(side=tk.LEFT)

    def update_file_list(self):
        """Update the list of files displayed in the listbox."""
        
        # Clear the current listbox contents 
        self.file_listbox.delete(0, tk.END)

        # List all files and directories in the current directory 
        for item in os.listdir(self.current_dir):
            self.file_listbox.insert(tk.END, item)

    def delete_item(self):
        selection = self.file_listbox.curselection()
        if selection:
           item = self.file_listbox.get(selection[0])
           item_path = os.path.join(self.current_dir, item)

           confirm = messagebox.askyesno("Confirm Delete", "Do you want to delete this item permanently?")
           if confirm:
               if os.path.isfile(item_path):
                   os.remove(item_path)
               elif os.path.isdir(item_path):
                   shutil.rmtree(item_path)
           else:
               shutil.move(item_path, self.bin_dir)
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

    def go_to_bin(self):
       """Navigate to the Bin directory."""
       self.current_dir = self.bin_dir
       self.path_label.config(text=self.current_dir)
       self.update_file_list()

    def run(self):
       """Run the Tkinter main loop."""
       self.root.mainloop()

if __name__ == "__main__":
   create_database()  # Ensure database is created before running the app
   login_app = LoginPage()  # Start with the login page
   login_app.mainloop()  # Run the login application loop