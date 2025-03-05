import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk  # For the Treeview widget

class AutomationWindow(tk.Toplevel):
    def __init__(self, parent, automation_folder, username):
        super().__init__(parent)
        self.title("Automation Window")
        self.geometry("600x400")  # Increased size
        self.automation_folder = automation_folder
        self.parent = parent
        self.username = username

        self.file_manager_button = tk.Button(self, text="Go to File Manager", command=self.go_to_file_manager)
        self.file_manager_button.pack()

        if not self.automation_folder:
            self.not_set_label = tk.Label(self, text="Automation folder not set.")
            self.not_set_label.pack()
            self.set_folder_button = tk.Button(self, text="Set Folder", command=self.set_automation_folder)
            self.set_folder_button.pack()
        else:
            self.folder_label = tk.Label(self, text=f"Automation Folder: {self.automation_folder}")
            self.folder_label.pack()
            self.open_folder_button = tk.Button(self, text="Open Folder", command=self.open_automation_folder)
            self.open_folder_button.pack()
            self.create_folder_button = tk.Button(self, text="Create Folders", command=self.create_multiple_folders)
            self.create_folder_button.pack()

            

            # Treeview Widget
            self.tree = ttk.Treeview(self)
            self.tree.pack(expand=True, fill=tk.BOTH)
            self.populate_tree()

    def go_to_file_manager(self):
        self.destroy()

    def set_automation_folder(self):
        parent_folder = filedialog.askdirectory(title="Select Parent Folder for Automation")
        if parent_folder:
            folder_name = simpledialog.askstring("Folder Name", "Enter name for the automation folder:")
            if folder_name:
                new_folder_path = os.path.join(parent_folder, folder_name)
                try:
                    os.makedirs(new_folder_path, exist_ok=True)
                    self.update_automation_folder_db(new_folder_path)
                    self.parent.automation_folder = new_folder_path
                    self.automation_folder = new_folder_path
                    # Update UI
                    if hasattr(self, 'not_set_label'):
                        self.not_set_label.destroy()
                    if hasattr(self, 'set_folder_button'):
                        self.set_folder_button.destroy()
                    self.folder_label = tk.Label(self, text=f"Automation Folder: {self.automation_folder}")
                    self.folder_label.pack()
                    self.open_folder_button = tk.Button(self, text="Open Folder", command=self.open_automation_folder)
                    self.open_folder_button.pack()
                    self.create_folder_button = tk.Button(self, text="Create Folders", command=self.create_multiple_folders)
                    self.create_folder_button.pack()

                    # Treeview Widget
                    self.tree = ttk.Treeview(self)
                    self.tree.pack(expand=True, fill=tk.BOTH)
                    self.populate_tree()
                    messagebox.showinfo("Success", f"Automation folder created at: {new_folder_path}")
                except OSError as e:
                    messagebox.showerror("Error", f"Failed to create folder: {e}")
        else:
            messagebox.showinfo("Cancelled", "Folder creation cancelled")

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
            cursor.execute('UPDATE users SET automation_folder = ? WHERE username = ?',
                           (automation_folder, self.username))  # Use self.username
            conn.commit()
        except Exception as e:
            messagebox.showerror(
                "Error", f"Could not update automation folder in the database: {e}")
        finally:
            conn.close()

    def create_multiple_folders(self):
        while True:
            folder_name = simpledialog.askstring("Folder Name", "Enter a folder name (or leave blank to finish):")
            if not folder_name:
                break
            new_folder_path = os.path.join(self.automation_folder, folder_name)
            try:
                os.makedirs(new_folder_path, exist_ok=True)
                messagebox.showinfo("Success", f"Folder '{folder_name}' created.")
            except OSError as e:
                messagebox.showerror("Error", f"Failed to create folder '{folder_name}': {e}")
                break
        self.populate_tree()  # Refresh the treeview

    def populate_tree(self):
        # Clear existing items in the tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree.heading("#0", text="Automation Folder Contents")
        self.insert_tree_items(self.automation_folder, "")

    def insert_tree_items(self, directory, parent):
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    self.tree.insert(parent, 'end', text=item, values=('file', item_path))
                elif os.path.isdir(item_path):
                    tree_id = self.tree.insert(parent, 'end', text=item, values=('folder', item_path), open=False)
                    self.insert_tree_items(item_path, tree_id)
        except Exception as e:
            messagebox.showerror("Error", f"Could not access directory: {e}")