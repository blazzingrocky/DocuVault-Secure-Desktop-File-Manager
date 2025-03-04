import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk
from automation import AutomationWindow

class FileManagerGUI: #The previous code is shortened
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DocuVault: Secure Desktop File Manager")
        self.root.geometry("600x400")
        self.bin_dir = "C:/Users/jbsch/OneDrive/Desktop/DocuVault/SWE_bin"


        choice = messagebox.askyesno("Directory Choice", "Do you want to start in the current directory?")
        if choice:
            self.current_dir = os.getcwd()
        else:
            self.current_dir = os.path.expanduser('~')  # Start in the user's home directory


        self.original_dir = self.current_dir  # Store the original directory
        self.automation_folder = None  # Initialize automation_folder


        self.create_widgets()
        self.update_file_list()


    def create_widgets(self):
        # Path label
        self.path_label = tk.Label(self.root, text=self.current_dir)
        self.path_label.pack()


        # Automation button
        self.automation_button = tk.Button(self.root, text="Automation Window", command=self.open_automation_window)
        self.automation_button.pack()


        # File listbox (replaced with Treeview for the main directory)
        self.file_tree = ttk.Treeview(self.root)
        self.file_tree.pack(expand=True, fill=tk.BOTH)
        self.file_tree.bind("<Double-1>", self.on_double_click)




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
            ("Go to Bin", self.go_to_bin),
            ("Restore", self.restore_item),
            ("Search", self.search_files)
        ]


        for text, command in buttons:
            button = tk.Button(self.buttons_frame, text=text, command=command)
            button.pack(side=tk.LEFT)
        self.search_results_window = None




    def search_files(self):
        search_term = simpledialog.askstring("Search", "Enter search term:")
        if search_term:
            original_dir = self.current_dir
            if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
                self.search_results_window.destroy()
            self.search_results_window = tk.Toplevel(self.root)
            self.search_results_window.title("Search Results")
            self.search_results_window.geometry("600x400")  # Increased width
            self.search_tree = ttk.Treeview(self.search_results_window)
            self.search_tree.pack(expand=True, fill=tk.BOTH)


            # Configure columns
            self.search_tree["columns"] = ("path",)
            self.search_tree.column("#0", width=200, minwidth=200)
            self.search_tree.column("path", width=400, minwidth=200)
            self.search_tree.heading("#0", text="Name")
            self.search_tree.heading("path", text="Path")


            # Perform recursive search and populate the tree
            self.recursive_search(self.current_dir, search_term, "")


            # Restore original directory
            self.current_dir = original_dir
            self.update_file_list()




    def recursive_search(self, start_dir, search_term, parent=""):
        try:
            for item in os.listdir(start_dir):
                item_path = os.path.join(start_dir, item)
                if search_term.lower() in item.lower():
                    # Use item as the text and full path as a value
                    self.search_tree.insert(parent, 'end', text=item, values=(item_path,), open=False)
           
                if os.path.isdir(item_path):
                    self.recursive_search(item_path, search_term, parent)
        except Exception as e:
            messagebox.showerror("Error", f"Could not access directory: {e}")






    def update_file_list(self):
        # Clear the treeview
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)


        # Repopulate the treeview with the current directory's contents
        self.populate_tree(self.file_tree, self.current_dir)
        self.path_label.config(text=self.current_dir)


    def populate_tree(self, tree, directory, parent=""):
        """Populates the treeview with files and folders from a directory."""
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    tree.insert(parent, 'end', text=item, values=('file', item_path))
                elif os.path.isdir(item_path):
                    tree_id = tree.insert(parent, 'end', text=item, values=('folder', item_path), open=False)
                    self.populate_tree(tree, item_path, tree_id)  # Recursive call
        except Exception as e:
            messagebox.showerror("Error", f"Could not access directory: {e}")




    def on_double_click(self, event):
        item_id = self.file_tree.selection()[0]  # Get selected item ID
        item_values = self.file_tree.item(item_id, 'values')  # Get values (type, path)


        if item_values:
            item_type, item_path = item_values
            if item_type == 'file':
                self.open_file(item_path)  # Open the selected file
            elif item_type == 'folder':
                self.go_into_directory(item_path)  # Navigate into the selected directory




    def open_file(self, item_path):
        """Opens file with default application."""
        text_extensions = ['.txt', '.py', '.html', '.css', '.js', '.md']  # More text-based file extensions
        file_extension = os.path.splitext(item_path)[1].lower()


        if file_extension in text_extensions:
            try:
                if os.name == 'nt':  # Windows
                    subprocess.Popen(['notepad.exe', item_path])  # Opens with Notepad
                elif os.name == 'posix':  # Linux/macOS
                    subprocess.Popen(['xdg-open', item_path])  # Opens with default text editor
            except FileNotFoundError:
                messagebox.showerror("Error", "Text editor not found.")
        else:
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(item_path)  # Opens with default application
                elif os.name == 'posix':  # Linux/macOS
                    subprocess.Popen(['xdg-open', item_path])  # Opens with default application
            except OSError:
                messagebox.showerror("Error", "Cannot open this file type.")


    def go_into_directory(self, item_path):
        """Navigates into the selected directory."""
        self.current_dir = item_path
        self.update_file_list()  # Update the file list to show the contents of the new directory






    def create_file(self):
        filename = simpledialog.askstring("Create File", "Enter file name:")
        if filename:
            try:
                with open(os.path.join(self.current_dir, filename), 'w') as f:
                    pass
                self.update_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Could not create file: {e}")




    def create_folder(self):
        foldername = simpledialog.askstring("Create Folder", "Enter folder name:")
        if foldername:
            try:
                os.makedirs(os.path.join(self.current_dir, foldername), exist_ok=True)
                self.update_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Could not create folder: {e}")




    def delete_item(self):
        selection = self.file_tree.selection() #Get the selected tree elements
        if selection:
            item_id = selection[0]  # Get the first selected item
            item_values = self.file_tree.item(item_id, 'values')


            if item_values:
                item_type, item_path = item_values


                confirm = messagebox.askyesno("Confirm Delete", "Do you want to delete this item permanently?")
                if confirm:
                    try:
                        if item_type == 'file':
                            os.remove(item_path)
                        elif item_type == 'folder':
                            shutil.rmtree(item_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not delete item: {e}")
                else:
                    if "SWE_bin" in item_path:
                        pass
                    else:
                        shutil.move(item_path, self.bin_dir)
                self.update_file_list()




    def move_item(self):
        selection = self.file_tree.selection()
        if selection:
            item_id = selection[0]
            item_values = self.file_tree.item(item_id, 'values')
            if item_values:
                item_type, item_path = item_values
                dest = filedialog.askdirectory(title="Select Destination Folder")
                if dest:
                    try:
                        shutil.move(item_path, dest)
                        self.update_file_list()
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not move item: {e}")




    def copy_item(self):
        selection = self.file_tree.selection()
        if selection:
            item_id = selection[0]
            item_values = self.file_tree.item(item_id, 'values')
            if item_values:
                item_type, item_path = item_values
                dest = filedialog.askdirectory(title="Select Destination Folder")
                if dest:
                    try:
                        if item_type == 'file':
                            shutil.copy2(item_path, dest)
                        elif item_type == 'folder':
                            shutil.copytree(item_path, os.path.join(dest, os.path.basename(item_path)))
                        self.update_file_list()
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not copy item: {e}")




    def go_to_parent_directory(self):
        if self.current_dir != os.path.expanduser("~"):
            self.current_dir = os.path.dirname(self.current_dir)
            self.update_file_list()


    def go_to_bin(self):
        self.current_dir = self.bin_dir
        self.update_file_list()


    def restore_item(self):
        selection = self.file_tree.selection()
        if selection:
            item_id = selection[0]
            item_values = self.file_tree.item(item_id, 'values')
            if item_values:
                item_type, item_path = item_values
                dest = filedialog.askdirectory(title="Select Destination Folder")
                if dest:
                    try:
                        shutil.move(item_path, dest)
                        self.update_file_list()
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not restore item: {e}")




    def run(self):
        """Run the Tkinter main loop."""
        self.root.mainloop()


    def get_username(self):
        conn = sqlite3.connect('docuvault.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        else:
            return None
    def open_automation_window(self):
        AutomationWindow(self.root, self.automation_folder)


    def get_automation_folder(self, username):
        conn = sqlite3.connect('docuvault.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT automation_folder FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return result[0]
        else:
            return None


    