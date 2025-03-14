import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk  # For the Treeview widget
from utility import CustomDirectoryDialog, compare_path
import requests
import json

class AutomationWindow(tk.Toplevel):
    def __init__(self, parent, automation_folder, username):
        super().__init__(parent)
        self.parent = parent
        self.title("Automation Window")
        self.geometry("600x400")
        self.automation_folder = automation_folder
       
        self.username = username


        self.file_manager_button = tk.Button(self, text="Go to File Manager", command=self.go_to_file_manager)
        self.file_manager_button.pack()


        if self.automation_folder is None or not os.path.exists(self.automation_folder):
            messagebox.showinfo("Info", "Automation folder does not exist. Please set it up.")
            self.auto_button = tk.Button(self, text="Set Automation Folder", command=self.set_automation_folder)
            self.auto_button.pack()
        else:
           
            self.current_dir = self.automation_folder
            self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')
            self.create_widgets()
            self.create_auto_folders()
            self.update_file_list()


    # In automation.py - modify the set_automation_folder method
    def create_auto_folders(self):
        self.folders = ["txt", "image"]
        for folder in self.folders:
            os.makedirs(os.path.join(self.automation_folder, folder), exist_ok=True)
        self.subfolders = {
            "txt": ["legal", "literary", "technical"],
            "image": ["jpg", "png"]
        }
        for folder, subfolders in self.subfolders.items():
            for subfolder in subfolders:
                os.makedirs(os.path.join(self.automation_folder, folder, subfolder), exist_ok=True)
        

    def set_automation_folder(self):
        dest_dialog = CustomDirectoryDialog(self.parent, os.path.expanduser("~"))
        self.parent.wait_window(dest_dialog)  # Wait for dialog to close
                
        if dest_dialog.selected_path:
            self.automation_folder = dest_dialog.selected_path
            # Update database
            conn = sqlite3.connect('docuvault.db')
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'UPDATE users SET automation_folder = ? WHERE username = ?',
                    (self.automation_folder, self.username)
                )
                conn.commit()
               
                # Immediately update FileManagerGUI's automation folder through parent
                if hasattr(self.master, 'update_automation_folder'):
                    self.master.update_automation_folder(self.automation_folder)
                   
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Update failed: {str(e)}")
            finally:
                conn.close()


            # Update local UI
            self.auto_button.destroy()
            self.current_dir = self.automation_folder
            self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')
            self.create_widgets()
            self.create_auto_folders()
            self.update_file_list()
       
        self.after(1000, self.update_file_list)  # Bring window to front after 1 second

    def create_widgets(self):
        self.path_label = tk.Label(self, text=self.current_dir)
        self.path_label.pack()


        self.file_tree = ttk.Treeview(self)
        self.file_tree.pack(expand=True, fill=tk.BOTH)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        self.file_tree.bind("<Button-3>", self.show_context_menu)  # Windows/Linux
        self.file_tree.bind("<Button-2>", self.show_context_menu)   # macOS

        self.buttons_frame = tk.Frame(self)
        self.buttons_frame.pack()


        buttons = [
            ("Create File", self.create_file),
            ("Create Folder", self.create_folder),
            ("Delete", self.delete_item),
            ("Move", self.move_item),
            ("Copy", self.copy_item),
            ("Go Back", self.go_to_parent_directory),
            ("Go to Bin", self.go_to_bin),
            ("Restore", self.restore_item),
            ("Search", self.search_files),
            ("Upload to Auto", self.upload_to_auto),
        ]


        for text, command in buttons:
            button = tk.Button(self.buttons_frame, text=text, command=command)
            button.pack(side=tk.LEFT)


        self.search_results_window = None


    def upload_to_auto(self):
        # selection = CustomDirectoryDialog(self.parent, self.current_dir)
        # self.parent.wait_window(selection)
        # selected_path = selection.selected_path
        selected_path = filedialog.askopenfilename(
            initialdir=self.current_dir,
            title="Select a file to upload"
        )
        
        if not selected_path:
            return
        
        if not os.path.isfile(selected_path):
            messagebox.showerror("Error", "Please select a file, not a directory")
            return

        # Create necessary directory structure
        self.classify_and_move(selected_path)
        self.update_file_list()

    def classify_and_move(self, selected_path):
        try:
            file_name = os.path.basename(selected_path)
            file_ext = os.path.splitext(file_name)[1].lower()

            dest_dir = self.automation_folder

            # Text file processing
            if file_ext == '.txt':
                # Verify AI service is running
                dest_dir = os.path.join(dest_dir, 'txt')
                category_map = {
                    0: 'legal',
                    1: 'literary',
                    2: 'technical'
                }
                try:
                    requests.get('http://localhost:8000/docs', timeout=2)
                except requests.ConnectionError:
                    messagebox.showerror(
                        "AI Service Offline",
                        "Text classification unavailable\n"
                        "Start file_auto_txt.py first"
                    )
                    return

                # Get AI classification
                with open(selected_path, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(
                        'http://localhost:8000/predict',
                        files=files,
                        timeout=5
                    )
                    response.raise_for_status()
                    category_idx = response.json()['category']
                    category_name = category_map.get(category_idx, 'unknown')
                    dest_dir = os.path.join(dest_dir, category_name)

            # Image file processing
            elif file_ext in ('.jpg', '.jpeg', '.png'):
                dest_dir = os.path.join(dest_dir, 'image')
                pass
            
            else:
                messagebox.showerror(
                    "Unsupported Format",
                    f"Cannot process {file_ext} files\n"
                    "Supported formats: .txt, .jpg, .png"
                )
                return

            # Ensure destination directory exists
            os.makedirs(dest_dir, exist_ok=True)
            
            # Generate unique filename
            base_name = os.path.splitext(file_name)[0]
            final_name = file_name
            counter = 1
            
            while os.path.exists(os.path.join(dest_dir, final_name)):
                final_name = f"{base_name}_{counter}{file_ext}"
                counter += 1
            
            dest_path = os.path.join(dest_dir, final_name)
            
            # Perform the file move
            shutil.move(selected_path, dest_path)
            
            # Prepare success message
            success_msg = (f"Moved to: {os.path.relpath(dest_path, self.automation_folder)}\n"
                        f"Location: {dest_path}")
            
            if file_ext == '.txt':
                success_msg = (f"Classified as {category_name}\n" + success_msg)
                
            messagebox.showinfo("Success", success_msg)
            
            # Refresh if in automation directory
            if compare_path(self.current_dir, self.automation_folder):
                self.update_file_list()

        except requests.HTTPError as e:
            messagebox.showerror(
                "Classification Error",
                f"API returned error: {e.response.text}"
            )
        except requests.Timeout:
            messagebox.showerror(
                "AI Timeout",
                "Classification service took too long to respond"
            )
        except Exception as e:
            messagebox.showerror(
                "Processing Error",
                f"Failed to handle file: {str(e)}"
            )

    def return_auto_folder(self):
        return self.automation_folder


    def go_to_file_manager(self):
        # Proper window destruction
        self.grab_release()  # Release modal grab
        self.destroy()

    def update_file_list(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        self.populate_tree(self.file_tree, self.current_dir)
        self.path_label.config(text=self.current_dir)


    def populate_tree(self, tree, directory, parent="", depth=0):
        """Recursively populate treeview with error handling"""
        try:
            # Skip system directories in Windows
            if os.name == 'nt' and any(sub in directory.lower() for sub in ('windows', 'program files', 'programdata')):
                return

            # Get directory contents with error handling
            try:
                items = os.listdir(directory)
            except PermissionError:
                if depth == 0:  # Only show error for top-level directory
                    messagebox.showwarning("Access Denied", 
                        f"Permission denied for directory:\n{directory}")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Could not access directory: {e}")
                return

            # Add parent directory entry
            if depth > 0:
                parent_dir = os.path.dirname(directory)
                tree.insert(parent, 'end', text="..", values=('parent', parent_dir), 
                        tags=('parent',), open=False)

            # Process items with rate limiting
            for idx, item in enumerate(items):
                if idx % 50 == 0:  # Prevent GUI freeze
                    tree.update_idletasks()
                    
                item_path = os.path.join(directory, item)
                try:
                    # Skip Windows system directories
                    if os.name == 'nt' and item.lower() in {'system volume information', 'recovery'}:
                        continue
                        
                    if os.path.isfile(item_path):
                        tree.insert(parent, 'end', text=item, values=('file', item_path))
                    elif os.path.isdir(item_path):
                        # Skip junction points and special directories
                        if os.name == 'nt' and os.stat(item_path).st_file_attributes & 1024:
                            continue
                            
                        tree_id = tree.insert(parent, 'end', text=item, 
                                        values=('folder', item_path), open=False)
                        # Limit recursion depth for stability
                        if depth < 3:
                            self.populate_tree(tree, item_path, tree_id, depth+1)
                            
                except PermissionError:
                    continue  # Skip items without access
                except Exception as e:
                    messagebox.showerror("Error", f"Could not process {item}")

        except Exception as e:
            messagebox.showerror("Critical Error", 
                f"Failed to populate directory structure: {str(e)}")


    def on_double_click(self, event):
        try:
            item_id = self.file_tree.selection()[0]
        except IndexError:
            return
        item_values = self.file_tree.item(item_id, 'values')
        if item_values:
            item_type, item_path = item_values
            if item_type == 'file':
                self.open_file(item_path)
            elif item_type == 'folder':
                self.go_into_directory(item_path)


    def open_file(self, item_path):
        text_extensions = ['.txt', '.py', '.html', '.css', '.js', '.md']
        file_extension = os.path.splitext(item_path)[1].lower()
        if file_extension in text_extensions:
            try:
                if os.name == 'nt':
                    subprocess.Popen(['notepad.exe', item_path])
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', item_path])
            except FileNotFoundError:
                messagebox.showerror("Error", "Text editor not found.")
        else:
            try:
                if os.name == 'nt':
                    os.startfile(item_path)
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', item_path])
            except OSError:
                messagebox.showerror("Error", "Cannot open this file type.")


    def go_into_directory(self, item_path):
        self.current_dir = item_path
        self.update_file_list()


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
        selection = self.file_tree.selection()
        if selection:
            item_id = selection[0]
            item_values = self.file_tree.item(item_id, 'values')
            if item_values:
                item_type, item_path = item_values
                confirm = messagebox.askyesnocancel("Confirm Delete", "Do you want to delete this item permanently?")
                if confirm is None:
                    return
                elif confirm:
                    try:
                        if item_type == 'file':
                            os.remove(item_path)
                        elif item_type == 'folder':
                            shutil.rmtree(item_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not delete item: {e}")
                else:
                    if "DocuVault_Bin" not in item_path:
                        shutil.move(item_path, self.bin_dir)
                self.update_file_list()


    def move_item(self):
        selection = self.file_tree.selection()
        if selection:
            item_id = selection[0]
            item_values = self.file_tree.item(item_id, 'values')
            if item_values:
                item_type, item_path = item_values
                dest_dialog = CustomDirectoryDialog(self.parent, self.current_dir)
                self.parent.wait_window(dest_dialog)  # Wait for dialog to close
                if dest_dialog.selected_path:
                    dest = dest_dialog.selected_path
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
                dest_dialog = CustomDirectoryDialog(self.parent, self.current_dir)
                self.parent.wait_window(dest_dialog)  # Wait for dialog to close
                if dest_dialog.selected_path:
                    dest = dest_dialog.selected_path
                    try:
                        if item_type == 'file':
                            shutil.copy2(item_path, dest)
                        elif item_type == 'folder':
                            shutil.copytree(item_path, os.path.join(dest, os.path.basename(item_path)))
                        self.update_file_list()
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not copy item: {e}")


    def go_to_parent_directory(self):
        if self.current_dir == self.automation_folder:
            messagebox.showinfo("Info", "Already in the root of Automation directory.")
            return
        if self.current_dir != os.path.expanduser("~"):
            self.current_dir = os.path.dirname(self.current_dir)
            self.update_file_list()
        else:
            messagebox.showinfo("Info", "Cannot go above the home directory.")

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
                dest_dialog = CustomDirectoryDialog(self.parent, self.current_dir)
                self.parent.wait_window(dest_dialog)
                
                if dest_dialog.selected_path:
                    dest = dest_dialog.selected_path
                    try:
                        shutil.move(item_path, dest)
                        self.update_file_list()
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not restore item: {e}")


    def search_files(self):
        search_term = simpledialog.askstring("Search", "Enter search term:")
        if search_term:
            original_dir = self.current_dir
            if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
                self.search_results_window.destroy()
       
            # self.search_results_window = tk.Toplevel(self.root)
            self.search_results_window = tk.Toplevel(self)
            self.search_results_window.title("Search Results")
            self.search_results_window.geometry("600x400")
       
            self.search_tree = ttk.Treeview(self.search_results_window)
            self.search_tree.pack(expand=True, fill=tk.BOTH)
            self.search_tree["columns"] = ("path",)
            self.search_tree.column("#0", width=200, minwidth=200)
            self.search_tree.column("path", width=400, minwidth=200)
            self.search_tree.heading("#0", text="Name")
            self.search_tree.heading("path", text="Path")

            self.search_tree.bind("<Button-3>", self.show_search_context_menu)  # Windows/Linux
            self.search_tree.bind("<Button-2>", self.show_search_context_menu)  # macOS
            self.search_tree.bind("<Double-1>", self.on_search_double_click)
       
            self.recursive_search(self.current_dir, search_term, "")
       
            self.current_dir = original_dir
            self.update_file_list()

    def on_search_double_click(self, event):
        item_id = self.search_tree.selection()[0]
        item_values = self.search_tree.item(item_id, 'values')
        if item_values:
            item_path = item_values[0]
            if os.path.isfile(item_path):
                self.open_file(item_path)
            elif os.path.isdir(item_path):
                self.go_into_directory(item_path)
                self.search_results_window.destroy()

    def show_search_context_menu(self, event):
        item = self.search_tree.identify('item', event.x, event.y)
        if item:
            self.search_tree.selection_set(item)
            item_values = self.search_tree.item(item, 'values')
            if item_values:
                item_path = item_values[0]
                context_menu = tk.Menu(self.parent, tearoff=0)
                context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
                context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
                context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                context_menu.add_command(label="Show in Folder", command=lambda: self.reveal_in_explorer(item_path))
                context_menu.post(event.x_root, event.y_root)


    def reveal_in_explorer(self, item_path):
        """Navigate to item's location in custom file manager and highlight it"""
        if not os.path.exists(item_path):
            messagebox.showerror("Error", "Path no longer exists")
            return

        # Determine target directory based on item type
        if os.path.isfile(item_path):
            target_dir = os.path.dirname(item_path)
            highlight_name = os.path.basename(item_path)
        else:  # Directory
            # For folders, go to parent directory and highlight the folder
            target_dir = os.path.dirname(os.path.normpath(item_path))
            highlight_name = os.path.basename(os.path.normpath(item_path))

        # Navigate to target directory
        self.current_dir = target_dir
        self.update_file_list()

        # Find and highlight the item
        for child in self.file_tree.get_children():
            item_text = self.file_tree.item(child, 'text')
            item_values = self.file_tree.item(child, 'values')
            
            # Match either by name or full path
            if item_text == highlight_name or \
            (item_values and compare_path(item_values[1], item_path)):
                self.file_tree.selection_set(child)
                self.file_tree.focus(child)
                self.file_tree.see(child)  # Scroll to make visible
                break

        # Bring window to front
        self.parent.lift()
        self.parent.attributes('-topmost', True)
        self.parent.after(100, lambda: self.parent.attributes('-topmost', False))

    def recursive_search(self, start_dir, search_term, parent=""):
        try:
            for item in os.listdir(start_dir):
                item_path = os.path.join(start_dir, item)
                if search_term.lower() in item.lower():
                    self.search_tree.insert(parent, 'end', text=item, values=(item_path,), open=False)
                if os.path.isdir(item_path):
                    self.recursive_search(item_path, search_term, parent)
        except Exception as e:
            messagebox.showerror("Error", f"Could not access directory: {e}")

    def show_context_menu(self, event):
        item = self.file_tree.identify('item', event.x, event.y)
        if item:
            self.file_tree.selection_set(item)
            item_values = self.file_tree.item(item, 'values')
            if item_values:
                item_type, item_path = item_values
                context_menu = tk.Menu(self.parent, tearoff=0)
                context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
                context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
                context_menu.add_command(label="Rename", command=lambda: self.rename_item(item))
                context_menu.add_command(label="Copy", command=lambda: self.copy_item())
                context_menu.add_command(label="Move", command=lambda: self.move_item())
                context_menu.add_command(label="Delete", command=lambda: self.delete_item())
                context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                if self.current_dir == self.bin_dir:
                    context_menu.add_command(label="Restore", command=lambda: self.restore_item())
                context_menu.post(event.x_root, event.y_root)


    def rename_item(self, item):
            new_name = simpledialog.askstring("Rename", "Enter new name:")
            if new_name:
                item_values = self.file_tree.item(item, 'values')
                if item_values:
                    item_type, item_path = item_values
                    new_path = os.path.join(os.path.dirname(item_path), new_name)
                    try:
                        os.rename(item_path, new_path)
                        self.update_file_list()
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not rename item: {e}")

    def copy_path(self, item_path):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(item_path)

    def get_available_apps(self, file_path):
        file_ext = os.path.splitext(file_path)[1].lower()
        available_apps = []

        if os.name == 'nt':  # Windows implementation
            # Add Default option first
            available_apps.append(("Default (System Default)", None))  # None indicates system default
            # Add common Windows applications
            common_apps = [
                ("Notepad", "notepad.exe"),
                ("WordPad", "write.exe"),
                ("Paint", "mspaint.exe"),
                ("Windows Photo Viewer", "rundll32.exe shimgvw.dll,ImageView_Fullscreen"),
                ("Microsoft Edge", "msedge.exe")
            ]
            
            # Check if apps exist in system paths
            system_paths = os.environ['PATH'].split(';')
            for name, exe in common_apps:
                for path in system_paths:
                    full_path = os.path.join(path, exe)
                    if os.path.exists(full_path):
                        available_apps.append((name, full_path))
                        break

        elif os.name == 'posix':  # Linux/macOS implementation
            try:
                # Get default application using xdg-mime
                mime_type = subprocess.check_output(
                    ['xdg-mime', 'query', 'filetype', file_path],
                    universal_newlines=True
                ).strip()
                
                default_app = subprocess.check_output(
                    ['xdg-mime', 'query', 'default', mime_type],
                    universal_newlines=True
                ).strip()
                
                if default_app:
                    available_apps.append(("Default", default_app))
                    
                # Find other available applications
                apps = subprocess.check_output(
                    ['grep', '-l', mime_type, 
                    '/usr/share/applications/*.desktop'],
                    universal_newlines=True
                ).split('\n')
                
                for app in apps:
                    if app:
                        app_name = os.path.basename(app).replace('.desktop', '')
                        available_apps.append((app_name, app))
                        
            except Exception as e:
                # Fallback common Linux apps
                common_apps = [
                    ("gedit", "gedit"),
                    ("LibreOffice", "libreoffice"),
                    ("GIMP", "gimp")
                ]
                available_apps.extend(common_apps)

        return available_apps


    def open_with(self, item_path):
        available_apps = self.get_available_apps(item_path)
        
        open_with_window = tk.Toplevel(self.parent)
        open_with_window.title("Open With")
        open_with_window.geometry("400x300")
        
        listbox = tk.Listbox(open_with_window)
        listbox.pack(expand=True, fill=tk.BOTH)
        
        for app_name, app_command in available_apps:
            listbox.insert(tk.END, app_name)
        
        def on_double_click(event):
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                app_name, app_command = available_apps[index]
                
                if app_command is None:  # This is the Default option
                    self.open_file(item_path)
                else:
                    try:
                        if os.name == 'nt':
                            subprocess.Popen([app_command, item_path])
                        elif os.name == 'posix':
                            if app_command.endswith('.desktop'):
                                subprocess.Popen(['gtk-launch', app_command, item_path])
                            else:
                                subprocess.Popen([app_command, item_path])
                    except Exception as e:
                        messagebox.showerror("Error", 
                            f"Could not open with {app_name}:\n{str(e)}")
                
                open_with_window.destroy()
        
        listbox.bind('<Double-1>', on_double_click)