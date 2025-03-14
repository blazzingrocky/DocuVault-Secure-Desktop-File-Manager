import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import stat
import shutil
import time
import sqlite3
import bcrypt
import subprocess
from tkinter import ttk  # For the Treeview widget
from tkinter import Menu
from automation import AutomationWindow
from utility import CustomDirectoryDialog, compare_path

def remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)  # Remove read-only flag
        func(path)

class FileManagerGUI:
    def __init__(self, username):
        self.root = tk.Tk()
        self.root.title("DocuVault: Secure Desktop File Manager")
        self.root.geometry("600x400")
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')
        os.makedirs(self.bin_dir, exist_ok=True)

        choice = messagebox.askyesno("Directory Choice", "Do you want to start in the current directory?")
        if choice:
            self.current_dir = os.getcwd()
        else:
            self.current_dir = os.path.expanduser('~')
        
        self.original_dir = self.current_dir
        self.username = username
        self.automation_folder = self.get_automation_folder(username)
        self.create_widgets()
        self.update_file_list()

    def create_widgets(self):
        self.path_label = tk.Label(self.root, text=self.current_dir)
        self.path_label.pack()
        self.automation_button = tk.Button(self.root, text="Automation Window", command=self.open_automation_window)
        self.root_button = tk.Button(self.root, text="🏠 Home", command=self.go_to_root)
        self.root_button.pack()
        self.automation_button.pack()
        self.file_tree = ttk.Treeview(self.root)
        self.file_tree.pack(expand=True, fill=tk.BOTH)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        self.file_tree.bind("<Button-3>", self.show_context_menu)
        self.buttons_frame = tk.Frame(self.root)
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
            ("Full Screen", self.toggle_fullscreen)
        ]
        for text, command in buttons:
            button = tk.Button(self.buttons_frame, text=text, command=command)
            button.pack(side=tk.LEFT)
        # self.fullscreen_button = tk.Button(self.buttons_frame, text="Full Screen", command=self.toggle_fullscreen)
        # self.fullscreen_button.pack(side=tk.LEFT)
        self.search_results_window = None
    
    def toggle_fullscreen(self):
        self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))
    def go_to_root(self):
        self.current_dir = os.path.expanduser('~')
        self.update_file_list()

    def search_files(self):
        search_term = simpledialog.askstring("Search", "Enter search term:")
        if search_term:
            original_dir = self.current_dir
            if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
                self.search_results_window.destroy()
            self.search_results_window = tk.Toplevel(self.root)
            self.search_results_window.title("Search Results")
            self.search_results_window.geometry("600x400")
            self.search_tree = ttk.Treeview(self.search_results_window)
            self.search_tree.pack(expand=True, fill=tk.BOTH)
            self.search_tree["columns"] = ("path",)
            self.search_tree.column("#0", width=200, minwidth=200)
            self.search_tree.column("path", width=400, minwidth=200)
            self.search_tree.heading("#0", text="Name")
            self.search_tree.heading("path", text="Path")

            self.search_tree.bind("<Button-3>", self.show_search_context_menu)
            self.search_tree.bind("<Button-2>", self.show_search_context_menu)  # For macOS
            self.search_tree.bind("<Double-1>", self.on_search_double_click)

            self.recursive_search(self.current_dir, search_term, "")
            self.current_dir = original_dir
            self.update_file_list()

    def recursive_search(self, start_dir, search_term, parent=""):
        try:
            items = os.listdir(start_dir)
        except PermissionError:
            return
        except Exception as e:
            messagebox.showerror("Error", f"Could not access directory: {e}")
            return

        for item in items:
            item_path = os.path.join(start_dir, item)
            try:
                if search_term.lower() in item.lower():
                    self.search_tree.insert(parent, 'end', 
                        text=item, values=(item_path,), open=False)
                    
                if os.path.isdir(item_path):
                    self.recursive_search(item_path, search_term, parent)
                    
            except PermissionError:
                continue
            except Exception as e:
                messagebox.showerror("Error", f"Could not process {item}")


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
                context_menu = Menu(self.root, tearoff=0)
                
                # Add context menu items
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
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))


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

    def show_context_menu(self, event):
        item = self.file_tree.identify('item', event.x, event.y)
        if item:
            self.file_tree.selection_set(item)
            item_values = self.file_tree.item(item, 'values')
            if item_values:
                item_type, item_path = item_values
                context_menu = Menu(self.root, tearoff=0)
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
        else:
            context_menu = Menu(self.root, tearoff=0)
            context_menu.add_command(label="Create File", command=self.create_file)
            context_menu.add_command(label="Create Folder", command=self.create_folder)
            context_menu.add_command(label="Bin", command=self.go_to_bin)
            context_menu.add_command(label="Refresh", command=self.update_file_list)
            context_menu.post(event.x_root, event.y_root)

    def rename_item(self, item):
        new_name = simpledialog.askstring("Rename", "Enter new name:")
        if new_name:
            item_values = self.file_tree.item(item, 'values')
            if item_values:
                item_type, item_path = item_values
                new_path = os.path.join(os.path.dirname(item_path), new_name)
                try:                    
                    # Check if destination already exists
                    if os.path.exists(new_path):
                        confirm = messagebox.askyesno("Confirm Overwrite", 
                            f"'{new_name}' already exists. Overwrite?")
                        if not confirm:
                            return
                        else:
                            if item_type == 'file':
                                os.remove(new_path)
                            elif item_type == 'folder':
                                shutil.rmtree(new_path, onexc=remove_readonly)
                    os.rename(item_path, new_path)
                    self.update_file_list()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not rename item: {e}")

    def copy_path(self, item_path):
        self.root.clipboard_clear()
        self.root.clipboard_append(item_path)

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
        
        open_with_window = tk.Toplevel(self.root)
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


    def open_file(self, item_path):
        if os.path.isfile(item_path):
            text_extensions = []
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
        elif os.path.isdir(item_path):
            self.go_into_directory(item_path)


    def go_into_directory(self, item_path):
        self.current_dir = item_path
        self.update_file_list()

    def create_file(self):
        filename = simpledialog.askstring("Create File", "Enter file name:")
        if not filename:
            return
        file_split=filename.split('.')
        count =0
        for i in file_split:
            if(len(i)>0):
                count+=1
        if(count<2 and len(file_split[-1])<=0):
            messagebox.showerror("Error", "Please enter a valid file name.")
            return
        
        file_path = os.path.join(self.current_dir, filename)        
        # Check if destination already exists
        if os.path.exists(file_path):
            confirm = messagebox.askyesno("Confirm Overwrite", 
                f"'{filename}' already exists. Overwrite?")
            if not confirm:
                return

        try:
            with open(os.path.join(self.current_dir, filename), 'w') as f:
                pass
            self.update_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not create file: {e}")

    def create_folder(self):
        foldername = simpledialog.askstring("Create Folder", "Enter folder name:")
        if not foldername:
            return
        folder_split=foldername.split('.')
        count =0
        for i in folder_split:
            if(len(i)>0):
                count+=1
        if(count==0):
            messagebox.showerror("Error", "Please enter a valid file name.")
            return
        
        folder_path = os.path.join(self.current_dir, foldername)
        # Check if destination already exists
        if os.path.exists(folder_path):
            confirm = messagebox.askyesno("Confirm Overwrite", 
                f"'{foldername}' already exists. Overwrite?")
            if not confirm:
                return
            else:
                shutil.rmtree(folder_path, onexc=remove_readonly)
        
        try:
            os.makedirs(folder_path, exist_ok=True)
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
                # Check if it's the automation folder
                if self.automation_folder and os.path.normpath(item_path) == os.path.normpath(self.automation_folder):
                    # Custom confirmation dialog for automation folder
                    confirm = messagebox.askokcancel(
                        "Delete Automation Folder",
                        "This is your automation folder. Deleting will remove all contents!\n\nAre you sure you want to permanently delete this folder?",
                        icon=messagebox.WARNING
                    )                  
                    if confirm:
                        try:
                            # Delete the automation folder and contents
                            shutil.rmtree(item_path, onexc=remove_readonly)
                        
                            # Update database
                            conn = sqlite3.connect('docuvault.db')
                            cursor = conn.cursor()
                            cursor.execute('UPDATE users SET automation_folder = NULL WHERE username = ?',(self.username,))
                            conn.commit()
                        
                            # Clear local reference
                            self.automation_folder = None
                            messagebox.showinfo("Success", "Automation folder and contents permanently deleted")
                        
                        except Exception as e:
                            messagebox.showerror("Error", f"Could not delete automation folder: {e}")
                        finally:
                            conn.close()
                            self.update_file_list()
                        return
                # Regular deletion process for non-automation items
                else:
                    if "DocuVault_Bin" not in item_path:
                        confirm = messagebox.askyesnocancel("Confirm Move to Bin",
                                    "Do you want to permanently delete this item?\n\n")
                        if confirm is None:
                            return
                        if confirm:
                            try:
                                if item_type == 'file':
                                    os.remove(item_path)
                                elif item_type == 'folder':
                                    shutil.rmtree(item_path, onexc=remove_readonly)
                            except Exception as e:
                                messagebox.showerror("Error", f"Could not delete item: {e}")
                        else:
                            shutil.move(item_path, self.bin_dir)
                        self.update_file_list()


                    else:
                        confirm = messagebox.askokcancel("Permanent Deletion",
                            "This will permanently delete the item!\n\nAre you absolutely sure?",
                            icon=messagebox.WARNING)
                        if confirm:
                            try:
                                if item_type == 'file':
                                    os.remove(item_path)
                                elif item_type == 'folder':
                                    shutil.rmtree(item_path, onexc=remove_readonly)
                            except Exception as e:
                                messagebox.showerror("Error", f"Could not delete item: {e}")
                            self.update_file_list()

    def move_item(self):
        selection = self.file_tree.selection()
        if selection:
            item_id = selection[0]
            item_values = self.file_tree.item(item_id, 'values')
            if item_values:
                item_type, item_path = item_values
                # Create custom dialog
                dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
                self.root.wait_window(dest_dialog)  # Wait for dialog to close
                
                if dest_dialog.selected_path:
                    dest = dest_dialog.selected_path
                    try:
                        base_name = os.path.basename(item_path)
                        dest_path = os.path.join(dest, base_name)
                        
                        # Check if destination already exists
                        if os.path.exists(dest_path):
                            confirm = messagebox.askyesno("Confirm Overwrite", 
                                f"'{base_name}' already exists in destination. Overwrite?")
                            if not confirm:
                                return
                            else:
                                if item_type == 'file':
                                    os.remove(dest_path)
                                elif item_type == 'folder':
                                    shutil.rmtree(dest_path, onexc=remove_readonly)
                            
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
                
                # Create custom dialog instance
                dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
                self.root.wait_window(dest_dialog)  # Wait for dialog to close
                
                if dest_dialog.selected_path:
                    dest = dest_dialog.selected_path
                    try:
                        # Get base name for folder copy
                        base_name = os.path.basename(item_path)
                        dest_path = os.path.join(dest, base_name)
                        
                        # Check if destination already exists
                        if os.path.exists(dest_path):
                            confirm = messagebox.askyesno("Confirm Overwrite", 
                                f"'{base_name}' already exists in destination. Overwrite?")
                            if not confirm:
                                return
                            else:
                                if item_type == 'file':
                                    os.remove(dest_path)
                                elif item_type == 'folder':
                                    shutil.rmtree(dest_path, onexc=remove_readonly)
                        
                        # Perform copy operation
                        if item_type == 'file':
                            shutil.copy2(item_path, dest)
                        elif item_type == 'folder':
                            shutil.copytree(item_path, dest_path)
                        
                        # Update UI and handle encryption
                        self.update_file_list()
                        # if self.is_encrypted(item_path):  # Assuming you have encryption checks
                        #     self.encrypt_file(dest_path)  # Re-encrypt if needed
                            
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not copy item: {str(e)}")
                    # finally:
                    #     # Update audit log
                    #     self.log_action("copy", item_path, dest)

    def go_to_parent_directory(self):
        if self.current_dir != os.path.expanduser("~"):
            self.current_dir = os.path.dirname(self.current_dir)
            self.update_file_list()
        else:
            messagebox.showinfo("Info", "Already at root directory")

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
                
                # Create custom directory dialog
                dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
                self.root.wait_window(dest_dialog)
                
                if dest_dialog.selected_path:
                    dest = dest_dialog.selected_path
                    try:
                        # Verify destination is different from bin
                        if dest == self.bin_dir:
                            messagebox.showwarning("Invalid Destination", 
                                "Cannot restore items back to the Recycle Bin")
                            return
                        
                        base_name = os.path.basename(item_path)
                        dest_path = os.path.join(dest, base_name)
                        
                        # Check if destination already exists
                        if os.path.exists(dest_path):
                            confirm = messagebox.askyesno("Confirm Overwrite", 
                                f"'{base_name}' already exists in destination. Overwrite?")
                            if not confirm:
                                return
                            else:
                                if item_type == 'file':
                                    os.remove(dest_path)
                                elif item_type == 'folder':
                                    shutil.rmtree(dest_path, onexc=remove_readonly)
                        # Perform restore operation
                        shutil.move(item_path, dest)
                        
                        # Update file list and restore original directory
                        self.update_file_list()
                        self.current_dir = self.bin_dir  # Stay in bin after restore
                        
                    except Exception as e:
                        messagebox.showerror("Restore Error", 
                            f"Could not restore item: {str(e)}")


    def run(self):
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

    def update_automation_folder(self, new_path):
        """Callback to update both instance variable and UI"""
        self.automation_folder = new_path
        self.update_file_list()  # Refresh display if in automation folder

    def open_automation_window(self):
        # Create automation window with proper parent relationship
        automation_win = AutomationWindow(self.root, self.automation_folder, self.username)
        automation_win.transient(self.root)  # Set proper window relationship
        automation_win.grab_set()  # Make it modal
        self.root.wait_window(automation_win)
        # Get updated folder after window closes
        self.automation_folder = automation_win.return_auto_folder()
        self.update_file_list()

    def get_automation_folder(self, username):
        conn = sqlite3.connect('docuvault.db')
        cursor = conn.cursor()
        cursor.execute('SELECT automation_folder FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return result[0]
        else:
            return None
