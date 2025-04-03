import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk, Menu
import os
import shutil
import sqlite3
import subprocess
import requests
from utility import CustomDirectoryDialog, CustomFileDialog, compare_path, txt_from_pdf
from database2 import log_action
from newfilemanager2 import FileManager, allow_access, restrict_access
from encryption_2 import FileEncryptor
import subprocess
import tempfile
import time
import threading
import os
from datetime import timedelta,datetime


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip, text=self.text,
                          background="#ffffe0", relief="solid", borderwidth=1,
                          padding=(5, 3))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class AutomationWindow(tk.Toplevel):
    def __init__(self, parent, automation_folder, username):
        super().__init__(parent)
        self.parent = parent
        self.title("Automation Dashboard")
        self.geometry("900x600")
        self.minsize(800, 500)
        self.automation_folder = automation_folder
        self.username = username
        self.sort_by = "name"
        self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')
        self.search_results_window = None
        self.initialize_encryption()
        
        # Configure window appearance
        try:
            self.iconbitmap(r"AppIcon\DocuVault-icon.ico")
        except:
            pass
            
        # Set up file manager for operations
        if hasattr(parent, 'file_manager'):
            self.file_manager = parent.file_manager
        else:
            self.file_manager = FileManager(username, self.bin_dir, None)

        # Initialize UI based on automation folder status
        if self.automation_folder is None or not os.path.exists(self.automation_folder):
            self.create_setup_ui()
        else:
            self.current_dir = self.automation_folder
            self.create_main_ui()
            self.create_auto_folders()
            self.update_file_list()

# Then add these methods to the AutomationWindow class

    def initialize_encryption(self):
        """Initialize the encryption system"""
        self.encryptor = FileEncryptor()
        self.encrypted_files = {}  # Track opened encrypted files
        self.file_watchers = {}    # Track file watchers for auto-encryption
        
    def encrypt_selected_files(self):
        """Encrypt selected files in the automation folder"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
            
        # Get master password if not set
        if not hasattr(self.encryptor, 'master_password') or not self.encryptor.master_password:
            password = simpledialog.askstring("Encryption Password", 
                                            "Enter encryption password:", 
                                            show='*')
            if not password:
                return
            self.encryptor.set_master_password(password)
            
        # Process each selected item
        encrypted_count = 0
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, 'values')
            if item_values and item_values[0] == 'file':
                file_path = item_values[1]
                
                # Skip already encrypted files
                if file_path.endswith('.enc'):
                    continue
                    
                try:
                    self.encryptor.encrypt_file(file_path)
                    # Remove original file
                    os.remove(file_path)
                    encrypted_count += 1
                except Exception as e:
                    messagebox.showerror("Encryption Error", f"Failed to encrypt {os.path.basename(file_path)}: {str(e)}")
                    
        # Update file list
        self.update_file_list()
    
        if encrypted_count > 0:
            messagebox.showinfo("Encryption Complete", f"Successfully encrypted {encrypted_count} file(s)")
        
    def decrypt_selected_files(self):
        """Decrypt selected files in the automation folder"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
            
        # Get master password if not set
        if not hasattr(self.encryptor, 'master_password') or not self.encryptor.master_password:
            password = simpledialog.askstring("Decryption Password", 
                                            "Enter decryption password:", 
                                            show='*')
            if not password:
                return
            self.encryptor.set_master_password(password)
            
        # Process each selected item
        decrypted_count = 0
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, 'values')
            if item_values and item_values[0] == 'file':
                file_path = item_values[1]
                
                # Skip non-encrypted files
                if not file_path.endswith('.enc'):
                    continue
                    
                try:
                    self.encryptor.decrypt_file(file_path)
                    # Remove encrypted file
                    os.remove(file_path)
                    decrypted_count += 1
                except Exception as e:
                    messagebox.showerror("Decryption Error", f"Failed to decrypt {os.path.basename(file_path)}: {str(e)}")
                    
        # Update file list
        self.update_file_list()
        
        if decrypted_count > 0:
            messagebox.showinfo("Decryption Complete", f"Successfully decrypted {decrypted_count} file(s)")
    def create_setup_ui(self):
        """Create UI for initial setup when automation folder doesn't exist yet"""
        setup_frame = ttk.Frame(self, padding=20)
        setup_frame.pack(expand=True, fill="both")
        
        # Header
        header_label = ttk.Label(setup_frame, text="Automation Setup", 
                                font=("Arial", 16, "bold"))
        header_label.pack(pady=20)
        
        # Info text
        info_text = ("Automation allows DocuVault to intelligently organize your files.\n"
                    "AI-powered classification will sort your documents and images into appropriate folders.")
        info_label = ttk.Label(setup_frame, text=info_text, wraplength=500, justify="center")
        info_label.pack(pady=20)
        
        # Setup button
        setup_btn = ttk.Button(setup_frame, text="Set Up Automation Folder", 
                              command=self.set_automation_folder, width=25)
        setup_btn.pack(pady=10)
        
        # Return button
        return_btn = ttk.Button(setup_frame, text="Return to File Manager", 
                               command=self.go_to_file_manager, width=25)
        return_btn.pack(pady=10)

    def create_main_ui(self):
        """Create the main UI with all automation features"""
        # Create styles
        style = ttk.Style()
        try:
            style.theme_use('vista' if os.name == 'nt' else 'clam')
        except tk.TclError:
            style.theme_use('default')
            
        # Top toolbar with navigation
        self.create_toolbar()
        
        # Main content area with file tree
        self.create_file_view()
        
        # Status bar
        self.create_status_bar()
    
    def create_toolbar(self):
        """Create the top toolbar with navigation and tools"""
        # Top frame
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation frame (left side)
        nav_frame = ttk.Frame(top_frame)
        nav_frame.pack(side=tk.LEFT)
        
        # Navigation buttons
        nav_buttons = [
            ("↩️", self.go_to_parent_directory, "Go Back"),
            ("🏠", lambda: self.navigate_to(self.automation_folder), "Home"),
            ("🔄", self.update_file_list, "Refresh"),
            ("🔍", self.search_files, "Search"),
            ("📂", self.go_to_file_manager, "Return to File Manager")
        ]
        
        for emoji, command, tooltip_text in nav_buttons:
            btn = ttk.Button(nav_frame, text=emoji, width=2, command=command)
            btn.pack(side=tk.LEFT, padx=2)
            Tooltip(btn, tooltip_text)
            
        # Path display (center)
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.path_label = ttk.Label(path_frame, text=self.automation_folder if self.automation_folder else "")
        self.path_label.pack(side=tk.LEFT)
        
        # Operations toolbar
        tools_frame = ttk.Frame(self)
        tools_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Left section: File operations
        left_section = ttk.Frame(tools_frame)
        left_section.pack(side=tk.LEFT)
        
        # "New" dropdown button
        new_btn = ttk.Button(left_section, text="New 🔽")
        new_btn.pack(side=tk.LEFT, padx=2)
        
        # New dropdown menu
        new_menu = tk.Menu(self, tearoff=0)
        new_menu.add_command(label="File", command=self.create_file)
        new_menu.add_command(label="Folder", command=self.create_folder)
        
        def show_new_menu(event=None):
            x = new_btn.winfo_rootx()
            y = new_btn.winfo_rooty() + new_btn.winfo_height()
            new_menu.post(x, y)
            
        new_btn.config(command=show_new_menu)
        
        # Sort dropdown
        sort_btn = ttk.Button(left_section, text="Sort 🔽")
        sort_btn.pack(side=tk.LEFT, padx=2)
        
        # Sort dropdown menu
        sort_menu = tk.Menu(self, tearoff=0)
        
        def sort_by_name():
            self.sort_by = "name"
            self.update_file_list()
            
        def sort_by_date():
            self.sort_by = "date"
            self.update_file_list()
            
        def sort_by_size():
            self.sort_by = "size"
            self.update_file_list()
            
        sort_menu.add_command(label="Name", command=sort_by_name)
        sort_menu.add_command(label="Date", command=sort_by_date)
        sort_menu.add_command(label="Size", command=sort_by_size)
        
        def show_sort_menu(event=None):
            x = sort_btn.winfo_rootx()
            y = sort_btn.winfo_rooty() + sort_btn.winfo_height()
            sort_menu.post(x, y)
            
        sort_btn.config(command=show_sort_menu)
        
        # Center section: Common operations
        center_section = ttk.Frame(tools_frame)
        center_section.pack(side=tk.LEFT, padx=20)
        
        operations = [
            ("Move", self.move_item),
            ("Copy", self.copy_item),
            ("Delete", self.delete_item),
            ("🔒Encrypt Files", self.encrypt_selected_files),
            ("🔓Decrypt Files", self.decrypt_selected_files),
        ]
        
        for text, command in operations:
            btn = ttk.Button(center_section, text=text, command=command)
            btn.pack(side=tk.LEFT, padx=2)
            
        # Right section: Automation features
        right_section = ttk.Frame(tools_frame)
        right_section.pack(side=tk.RIGHT)
        
        upload_btn = ttk.Button(right_section, text="Upload & Classify", 
                              command=self.upload_to_auto)
        upload_btn.pack(side=tk.RIGHT, padx=5)
        Tooltip(upload_btn, "Upload a file for AI classification")

    def create_file_view(self):
        """Create the file tree view"""
        # Create a frame for the file tree and scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # File tree (main content)
        self.file_tree = ttk.Treeview(tree_frame, selectmode="extended")
        self.file_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.file_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.configure(yscrollcommand=vsb.set)
        
        # Set up event bindings
        self.file_tree.bind('<Control-a>', self.select_all)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        self.file_tree.bind("<Button-3>", self.show_context_menu)
        self.file_tree.bind("<Button-1>", self.deselect_on_empty_space, add="+")

    def create_status_bar(self):
        """Create the status bar at the bottom of the window"""
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Status message
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=3)
        
        # Item count
        self.count_label = ttk.Label(status_frame, text="")
        self.count_label.pack(side=tk.RIGHT, padx=10, pady=3)

    def update_status(self, message, count=None):
        """Update the status bar information"""
        self.status_label.config(text=message)
        if count is not None:
            self.count_label.config(text=f"{count} items")

    def create_auto_folders(self):
        """Create the default folder structure for automation"""
        self.folders = ["txt", "image", "pdf"]
        for folder in self.folders:
            os.makedirs(os.path.join(self.automation_folder, folder), exist_ok=True)
            
        self.subfolders = {
            "txt": ["legal", "literary", "technical"],
            "image": [],
            "pdf": ["legal", "literary", "technical"]
        }
        
        for folder, subfolders in self.subfolders.items():
            for subfolder in subfolders:
                os.makedirs(os.path.join(self.automation_folder, folder, subfolder), exist_ok=True)

    def set_automation_folder(self):
        """Set up the automation folder structure"""
        confirm = messagebox.askyesno("Automation Setup", 
                                     "Do you want to set up the AI-powered file automation?")
        if confirm:
            self.automation_folder = os.path.join(os.path.expanduser("~"), 
                                               f"Automation_Window_{self.username}")
            os.makedirs(self.automation_folder, exist_ok=True)
            
            # Update database
            conn = sqlite3.connect('docuvault.db')
            conn.execute('PRAGMA foreign_keys = ON')
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    'UPDATE users SET automation_folder = ? WHERE username = ?',
                    (self.automation_folder, self.username)
                )
                conn.commit()
                
                # Update parent if it's the FileManagerGUI
                if hasattr(self.parent, 'update_automation_folder'):
                    self.parent.update_automation_folder(self.automation_folder)
                    
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Update failed: {str(e)}")
            finally:
                conn.close()
                
            # Recreate the UI now that we have an automation folder
            for widget in self.winfo_children():
                widget.destroy()
                
            self.current_dir = self.automation_folder
            self.create_main_ui()
            self.create_auto_folders()
            self.update_file_list()
            self.update_status("Automation folder created successfully")

    # Navigation and file display methods
    def navigate_to(self, path):
        """Navigate to the specified directory"""
        if os.path.isdir(path):
            try:
                # Check if we can access this directory
                os.listdir(path)
                # If successful, update current_dir and refresh
                self.current_dir = path
                self.update_file_list()
            except PermissionError:
                messagebox.showwarning("Access Denied", 
                                      f"Permission denied for directory:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not access directory: {str(e)}")

    def update_file_list(self):
        """Update the file tree with contents of the current directory"""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        # Populate tree with new items
        self.populate_tree(self.file_tree, self.current_dir)
        
        # Update path label and status
        self.path_label.config(text=self.current_dir)
        
        # Update item count
        try:
            count = len(os.listdir(self.current_dir))
            self.update_status("Ready", count)
        except:
            self.update_status("Error reading directory")

    def populate_tree(self, tree, directory, parent="", depth=0):
        """Recursively populate treeview with directory contents"""
        try:
            # Skip system directories in Windows
            if os.name == 'nt' and any(sub in directory.lower() 
                                       for sub in ('windows', 'program files', 'programdata')):
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
                if depth == 0:
                    messagebox.showerror("Error", f"Could not access directory: {e}")
                return
                
            # Helper functions for sorting
            def safe_getsize(item):
                try:
                    return os.path.getsize(os.path.join(directory, item))
                except:
                    return 0
                    
            def safe_getmtime(item):
                try:
                    return os.path.getmtime(os.path.join(directory, item))
                except:
                    return 0
                    
            # Sort items based on the selected criteria
            if self.sort_by == "name":
                items = sorted(items)
            elif self.sort_by == "size":
                items = sorted(items, key=safe_getsize, reverse=True)
            elif self.sort_by == "date":
                items = sorted(items, key=safe_getmtime, reverse=True)
                
            # Add parent directory entry
            if depth > 0:
                parent_dir = os.path.dirname(directory)
                tree.insert(parent, 'end', text="..", values=('parent', parent_dir),
                          tags=('parent',), open=False)
                
            # Process items with rate limiting to prevent GUI freeze
            for idx, item in enumerate(items):
                if idx % 50 == 0:  # Update UI occasionally
                    tree.update_idletasks()
                    
                item_path = os.path.join(directory, item)
                
                try:
                    # Skip Windows system directories
                    if os.name == 'nt' and item.lower() in {'system volume information', 'recovery'}:
                        continue
                        
                    if os.path.isfile(item_path):
                        # Add icon based on file type
                        ext = os.path.splitext(item)[1].lower()
                        if ext in ['.txt', '.doc', '.docx', '.pdf']:
                            icon = "📄 "  # Document icon
                        elif ext in ['.jpg', '.jpeg', '.png', '.gif']:
                            icon = "🖼️ "  # Image icon
                        elif ext in ['.mp4', '.avi', '.mov']:
                            icon = "🎬 "  # Video icon
                        elif ext in ['.mp3', '.wav']:
                            icon = "🎵 "  # Audio icon
                        else:
                            icon = "📄 "  # Generic file icon
                            
                        tree.insert(parent, 'end', text=f"{icon}{item}", values=('file', item_path))
                    elif os.path.isdir(item_path):
                        # Skip junction points and special directories
                        if os.name == 'nt' and os.stat(item_path).st_file_attributes & 1024:
                            continue
                            
                        # Add folder icon
                        tree_id = tree.insert(parent, 'end', text=f"📁 {item}",
                                            values=('folder', item_path), open=False)
                                            
                        # Limit recursion depth for stability
                        if depth < 3:
                            self.populate_tree(tree, item_path, tree_id, depth+1)
                except PermissionError:
                    continue  # Skip items without access
                except Exception as e:
                    continue  # Skip problematic items
                    
        except Exception as e:
            if depth == 0:
                self.update_status(f"Error: {str(e)}")

    # Event handlers and UI interactions
    def on_double_click(self, event):
        """Handle double-click on file tree items"""
        try:
            item_id = self.file_tree.selection()[0]
        except IndexError:
            return
            
        item_values = self.file_tree.item(item_id, 'values')
        if item_values:
            item_type, item_path = item_values
            
            if item_type == 'file':
                self.open_file(item_path)
            elif item_type == 'folder' or item_type == 'parent':
                self.navigate_to(item_path)

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        # Identify the item that was right-clicked
        clicked_item = self.file_tree.identify('item', event.x, event.y)
        
        if clicked_item:
            # Check if the clicked item is already selected
            current_selection = self.file_tree.selection()
            
            # If clicked item is not in current selection, make it the only selection
            if clicked_item not in current_selection:
                self.file_tree.selection_set(clicked_item)
                
            # Get the item values of the clicked item
            item_values = self.file_tree.item(clicked_item, 'values')
            
            if item_values:
                item_type, item_path = item_values
                
                context_menu = Menu(self, tearoff=0)
                
                if item_type == 'file':
                    context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
                    context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
                    context_menu.add_separator()
                    
                context_menu.add_command(label="Rename", command=lambda: self.rename_item(clicked_item))
                context_menu.add_command(label="Copy", command=self.copy_item)
                context_menu.add_command(label="Move", command=self.move_item)
                context_menu.add_command(label="Delete", command=self.delete_item)
                context_menu.add_separator()
                context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                
                if item_type == 'file':
                    context_menu.add_separator()
                    context_menu.add_command(label="Classify This File", 
                                          command=lambda: self.classify_and_upload(item_path))
                context_menu.add_separator()



                if self.encryptor.is_file_encrypted(item_path):
                    context_menu.add_command(label="Decrypt", command=self.decrypt_selected_files)
                else:
                    context_menu.add_command(label="Encrypt", command=self.encrypt_selected_files)
                    
                context_menu.tk_popup(event.x_root, event.y_root)
        else:
            # Clicked on empty space - show different context menu
            context_menu = Menu(self, tearoff=0)
            context_menu.add_command(label="Create File", command=self.create_file)
            context_menu.add_command(label="Create Folder", command=self.create_folder)
            context_menu.add_separator()
            context_menu.add_command(label="Refresh", command=self.update_file_list)
            context_menu.add_command(label="Upload & Classify File", command=self.upload_to_auto)
            
            # Deselect all items when right-clicking on empty space
            self.file_tree.selection_set([])
            self.file_tree.focus("")
            
            context_menu.tk_popup(event.x_root, event.y_root)

    def deselect_on_empty_space(self, event):
        """Deselect all items when clicking on empty space"""
        # Get the item (row) that was clicked
        item = self.file_tree.identify_row(event.y)
        
        # If not clicking on a row (empty space), clear selection
        if not item:
            self.file_tree.selection_set([])
            self.file_tree.focus("")
            return "break"

    def select_all(self, event=None):
        """Select all items in the file tree"""
        for item in self.file_tree.get_children():
            self.file_tree.selection_add(item)
        return "break"

    # File operations
    def go_to_parent_directory(self):
        """Navigate to the parent directory"""
        if self.current_dir == self.automation_folder:
            messagebox.showinfo("Info", "Already in the root of Automation directory.")
            return
            
        if self.current_dir != os.path.expanduser("~"):
            self.current_dir = os.path.dirname(self.current_dir)
            self.update_file_list()
        else:
            messagebox.showinfo("Info", "Cannot go above the home directory.")

    def go_to_file_manager(self):
        """Return to the main file manager"""
        self.grab_release()  # Release modal grab if any
        self.destroy()
    def open_file(self, item_path):
        """Override open_file to handle encrypted files"""
        # Check if the file is encrypted
        is_encrypted = item_path.endswith('.enc')
        
        if is_encrypted:
            # Get master password if not set
            if not hasattr(self.encryptor, 'master_password') or not self.encryptor.master_password:
                password = simpledialog.askstring("Decryption Password", 
                                                "Enter decryption password:", 
                                                show='*')
                if not password:
                    return
                self.encryptor.set_master_password(password)
                
            try:
                # Decrypt to a temporary file
                temp_file = self.encryptor.decrypt_file(item_path, temp=True)
                
                # Open the temporary file
                if os.path.isfile(temp_file):
                    success, message = self.file_manager.open_file(temp_file)
                    
                    if not success:
                        messagebox.showerror("Error", message)
                        # Clean up temp file if open fails
                        self.encryptor.cleanup_temp_file(temp_file)
                        return
                        
                    # Start a file watcher to monitor when the file is closed
                    self.start_file_watcher(temp_file, item_path)
                    
                    # Track the opened encrypted file
                    self.encrypted_files[temp_file] = item_path
                    
                    return
            except Exception as e:
                messagebox.showerror("Decryption Error", f"Failed to decrypt file: {str(e)}")
                return
        else:
            # Regular file opening
            if os.path.isfile(item_path):
                success, message = self.file_manager.open_file(item_path)
                if not success:
                    messagebox.showerror("Error", message)
            elif os.path.isdir(item_path):
                self.navigate_to(item_path)
            else:
                messagebox.showinfo("Info", "Selected item cannot be opened")
            
    def start_file_watcher(self, temp_file, original_encrypted_file):
        """Start a thread to watch for file modifications and handle re-encryption"""
        if temp_file in self.file_watchers:
            # Stop existing watcher
            self.file_watchers[temp_file]['running'] = False
            
        # Create a new watcher thread
        watcher_data = {'running': True, 'last_modified': os.path.getmtime(temp_file)}
        self.file_watchers[temp_file] = watcher_data
        
        def watch_file():
            check_interval = 2  # seconds
            inactivity_threshold = 10  # seconds
            last_activity = time.time()
            
            while watcher_data['running']:
                try:
                    if os.path.exists(temp_file):
                        current_mtime = os.path.getmtime(temp_file)
                        
                        # Check if file was modified
                        if current_mtime != watcher_data['last_modified']:
                            watcher_data['last_modified'] = current_mtime
                            last_activity = time.time()
                        
                        # Check if file has been inactive for the threshold period
                        if time.time() - last_activity > inactivity_threshold:
                            # Re-encrypt the file
                            try:
                                self.encryptor.encrypt_file(temp_file, original_encrypted_file)
                                # Remove the temp file
                                os.remove(temp_file)
                                # Remove from tracking
                                if temp_file in self.encrypted_files:
                                    del self.encrypted_files[temp_file]
                                # Stop the watcher
                                watcher_data['running'] = False
                                break
                            except Exception as e:
                                print(f"Error re-encrypting file: {str(e)}")
                    else:
                        # File no longer exists, stop watching
                        watcher_data['running'] = False
                        break
                except Exception as e:
                    print(f"Error in file watcher: {str(e)}")
                time.sleep(check_interval)
    # def open_file(self, item_path):
    #     """Open a file with the default application"""
    #     if os.path.isfile(item_path):
    #         success, message = self.file_manager.open_file(item_path)
    #         if not success:
    #             messagebox.showerror("Error", message)
                
    #     elif os.path.isdir(item_path):
    #         self.navigate_to(item_path)
    #     else:
    #         messagebox.showinfo("Info", "Selected item cannot be opened")

    def open_with(self, item_path):
        """Open a file with a selected application"""
        available_apps = self.file_manager.get_available_apps(item_path)
        
        if not available_apps:
            messagebox.showinfo("Info", "No applications found to open this file")
            return
            
        app_window = tk.Toplevel(self)
        app_window.title("Open With")
        app_window.geometry("400x300")
        
        # Add header
        ttk.Label(app_window, text="Choose an application:", padding=10).pack()
        
        # Create listbox with applications
        listbox = tk.Listbox(app_window)
        listbox.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        for app in available_apps:
            listbox.insert(tk.END, app[0])
            
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
                
                app_window.destroy()
                
        listbox.bind('<Double-1>', on_double_click)
        
        # Add buttons
        button_frame = ttk.Frame(app_window, padding=10)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Open", 
                 command=lambda: on_double_click(None)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                 command=app_window.destroy).pack(side=tk.RIGHT, padx=5)

    def create_file(self):
        """Create a new file"""
        filename = simpledialog.askstring("Create File", "Enter file name:")
        if filename:
            success, message = self.file_manager.create_file(self.current_dir, filename)
            if success:
                self.update_file_list()
                self.update_status(f"Created file: {filename}")
            else:
                messagebox.showerror("Error", message)

    def create_folder(self):
        """Create a new folder"""
        foldername = simpledialog.askstring("Create Folder", "Enter folder name:")
        if foldername:
            success, message = self.file_manager.create_folder(self.current_dir, foldername)
            if success:
                self.update_file_list()
                self.update_status(f"Created folder: {foldername}")
            else:
                messagebox.showerror("Error", message)

    def rename_item(self, item_id):
        """Rename a file or folder"""
        item_values = self.file_tree.item(item_id, 'values')
        if item_values:
            item_type, item_path = item_values
            old_name = os.path.basename(item_path)
            new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=old_name)
            
            if new_name and new_name != old_name:
                success, message = self.file_manager.rename_item(item_path, new_name)
                if success:
                    self.update_file_list()
                    self.update_status(f"Renamed to: {new_name}")
                else:
                    messagebox.showerror("Error", message)

    def delete_item(self):
        """Delete selected files/folders"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
            
        items_to_delete = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        num_items = len(items_to_delete)
        
        response = messagebox.askyesnocancel("Delete Items",
            f"What would you like to do with the selected {'item' if num_items==1 else f'{num_items} items'}?\n\n"
            f"Yes = Delete permanently\nNo = Move to Bin\nCancel = Abort operation")
            
        if response is None:  # Cancel
            return
            
        if response:
            result = self.file_manager.delete_item(self.current_dir, items_to_delete, permanently=True)
        else:
            result = self.file_manager.delete_item(self.current_dir, items_to_delete)
            
        if result["success_count"] > 0:
            self.update_status(f"Successfully {'deleted' if response else 'moved to bin'} "
                             f"{result['success_count']} item(s)")
                             
        if result["failed_items"]:
            failed_msg = "\n".join(result["failed_items"])
            messagebox.showerror("Error", f"Failed to delete some items:\n{failed_msg}")
            
        self.update_file_list()

    def move_item(self):
        """Move selected files/folders to a new location"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
            
        items_to_move = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.parent, self.current_dir)
        self.parent.wait_window(dest_dialog)  # Wait for dialog to close
        
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.move_item(items_to_move, destination)
            print("No of items moved: ", result["success_count"])
            if result["success_count"] > 0:
                messagebox.showinfo("Success", f"Successfully moved {result['success_count']} item(s) to {result['destination']}")
            
            if result["failed_items"]:
                failed_msg = "\n".join(result["failed_items"])
                messagebox.showerror("Error", f"Failed to move some items:\n{failed_msg}")
            
            if result["skipped_items"]:
                skipped_msg = "\n".join(result["skipped_items"])
                messagebox.showinfo("Info", f"Skipped items:\n{skipped_msg}")
                
        self.update_file_list()

    def copy_item(self):
        """Copy selected files/folders to a new location"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
            
        items_to_copy = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.parent, self.current_dir)
        self.parent.wait_window(dest_dialog)  # Wait for dialog to close
        
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.copy_item(items_to_copy, destination)
            if result["success_count"] > 0:
                messagebox.showinfo("Success", f"Successfully copied {result['success_count']} item(s) to {result['destination']}")
            
            if result["failed_items"]:
                failed_msg = "\n".join(result["failed_items"])
                messagebox.showerror("Error", f"Failed to copy some items:\n{failed_msg}")
        self.update_file_list()

    def copy_path(self, item_path):
        """Copy file/folder path to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(item_path)
        self.update_status(f"Path copied to clipboard: {item_path}")
    def search_files(self):
        self.grab_release()
        original_dir = self.current_dir
        if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
            self.search_results_window.destroy()
        
        self.search_results_window = tk.Toplevel(self.parent)
        self.search_results_window.title("Search Files")
        self.search_results_window.geometry("800x600")
        
        # Create search frame at top
        search_frame = ttk.Frame(self.search_results_window, padding=10)
        search_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Search bar
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        search_button = ttk.Button(search_frame, text="Search", command=self.perform_search)
        search_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Filter options frame
        filter_frame = ttk.LabelFrame(self.search_results_window, text="Filter Options", padding=10)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # File type filter
        ttk.Label(filter_frame, text="File Type:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.file_type_var = tk.StringVar()
        file_types = ["All Files", "Documents (.txt, .pdf, .doc, .ppt)", "Images (.jpg, .png, .gif)", "Videos (.mp4, .avi, .mov)", "Audio (.mp3, .wav)"]
        file_type_combo = ttk.Combobox(filter_frame, textvariable=self.file_type_var, values=file_types, width=25, state='readonly')
        file_type_combo.current(0)
        file_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Date modified filter
        ttk.Label(filter_frame, text="Date Modified:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.date_var = tk.StringVar()
        date_options = ["Any Time", "Today", "This Week", "This Month", "This Year"]
        date_combo = ttk.Combobox(filter_frame, textvariable=self.date_var, values=date_options, width=15, state='readonly')
        date_combo.current(0)
        date_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Size filter
        ttk.Label(filter_frame, text="Size:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.size_var = tk.StringVar()
        size_options = ["Any Size", "Small (<1MB)", "Medium (1-100MB)", "Large (>100MB)"]
        size_combo = ttk.Combobox(filter_frame, textvariable=self.size_var, values=size_options, width=25, state='readonly')
        size_combo.current(0)
        size_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Search location
        ttk.Label(filter_frame, text="Search In:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.location_var = tk.StringVar(value=self.current_dir)
        location_entry = ttk.Entry(filter_frame, textvariable=self.location_var, width=30, state='readonly')
        location_entry.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        # Browse button
        
        browse_button = ttk.Button(filter_frame, text="...", width=3, 
                                command=lambda: self.browse_for_search_location())
        # Set the button to be disabled if no folder is selected
        browse_button.grid(row=1, column=4, padx=2, pady=5)
        
        # Reset filters button
        reset_button = ttk.Button(filter_frame, text="Reset Filters", command=self.reset_search_filters)
        reset_button.grid(row=1, column=5, padx=5, pady=5)
        
        # Create the search results treeview
        results_frame = ttk.Frame(self.search_results_window)
        results_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Add a label for results count
        self.results_count_label = ttk.Label(results_frame, text="Results: 0 items found")
        self.results_count_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create treeview with scrollbars
        self.search_tree = ttk.Treeview(results_frame)
        self.search_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.search_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.search_tree.configure(yscrollcommand=vsb.set)
        
        # Configure treeview columns
        self.search_tree["columns"] = ("name", "path", "type", "size", "modified")
        self.search_tree.column("#0", width=40, minwidth=40)  # Icon column
        self.search_tree.column("name", width=200, minwidth=100)
        self.search_tree.column("path", width=300, minwidth=100)
        self.search_tree.column("type", width=100, minwidth=80)
        self.search_tree.column("size", width=100, minwidth=80)
        self.search_tree.column("modified", width=150, minwidth=100)
        
        self.search_tree.heading("#0", text="")
        self.search_tree.heading("name", text="Name")
        self.search_tree.heading("path", text="Path")
        self.search_tree.heading("type", text="Type")
        self.search_tree.heading("size", text="Size")
        self.search_tree.heading("modified", text="Date Modified")
        
        # Bind events
        self.search_tree.bind("<Double-1>", self.on_search_double_click)
        self.search_tree.bind("<Button-3>", self.show_search_context_menu)
        self.search_entry.bind("<Return>", lambda e: self.perform_search())
        
        # Set focus to search entry
        self.search_entry.focus_set()
        
        # Add status bar
        status_bar = ttk.Frame(self.search_results_window)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=2)
        self.search_status = ttk.Label(status_bar, text="Search for files...")
        self.search_status.pack(side=tk.LEFT, padx=10)
        
        # Initialize empty results
        self.local_results_found = False
        self.search_results = []

        self.search_results_window.protocol("WM_DELETE_WINDOW", self.on_search_window_close)
    
    def browse_for_search_location(self):
        """Open a directory dialog to select search location"""
        # Check if the current window is already grabbed
        if self.grab_current() == self.search_results_window:
            return
        # Check if the current window is already grabbed
    # Release grab before dialog
        self.grab_release()
        
        dest_dialog = CustomDirectoryDialog(self, self.current_dir)
        self.wait_window(dest_dialog)  # Wait for dialog to close
        
        if dest_dialog.selected_path:
            self.location_var.set(dest_dialog.selected_path)
        
        # Re-grab after dialog is closed
        self.grab_set()
    def perform_search(self):
        """Execute search with current filters"""
        search_term = self.search_entry.get()
        if not search_term:
            messagebox.showinfo("Search", "Please enter a search term")
            return
        
        # Clear previous results
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        # Update status
        self.search_status.config(text="Searching...")
        self.search_results_window.update_idletasks()
        
        # Get filter values
        search_dir = self.location_var.get()
        file_type = self.file_type_var.get()
        date_filter = self.date_var.get()
        size_filter = self.size_var.get()
        
        # Convert file type filter to extensions
        extensions = []
        if file_type == "Documents (.txt, .pdf, .doc, .ppt)":
            extensions = ['.txt', '.pdf', '.doc', '.docx', '.rtf', '.odt', '.ppt', '.pptx', '.xls', '.xlsx']
        elif file_type == "Images (.jpg, .png, .gif)":
            extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        elif file_type == "Videos (.mp4, .avi, .mov)":
            extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
        elif file_type == "Audio (.mp3, .wav)":
            extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma']
        
        # Get current time for date filtering
        current_time = datetime.now()
        date_limit = None
        
        if date_filter == "Today":
            date_limit = current_time - timedelta(days=1)
        elif date_filter == "This Week":
            date_limit = current_time - timedelta(days=7)
        elif date_filter == "This Month":
            date_limit = current_time - timedelta(days=30)
        elif date_filter == "This Year":
            date_limit = current_time - timedelta(days=365)
        
        # Track results
        self.search_results = []
        self.local_results_found = False
        
        # Start the search
        self.recursive_search_with_filters(search_dir, search_term, extensions, date_limit, size_filter)
        
        # Update results count
        result_count = len(self.search_tree.get_children())
        self.results_count_label.config(text=f"Results: {result_count} items found")
        
        # Display message if no results found
        if not self.local_results_found:
            self.search_tree.insert("", "end", text="", values=("No matching results found", "", "", "", ""))
        
        # Update status
        self.search_status.config(text="Search completed")
        
        # Ask about cloud search
        # if messagebox.askyesno("Cloud Search", "Search in Nextcloud storage?"):
        #     if self.cloud and self.cloud.nc:
        #         self.cloud.search_files(search_term, callback=self.display_cloud_results)
        #     else:
        #         messagebox.showinfo("Cloud Search", "Please connect to cloud first")
        
        # Bring search window back to focus
        self.search_results_window.lift()
        self.search_results_window.focus_set()
    def on_search_window_close(self):
        self.search_results_window.destroy()
        self.search_results_window = None
        # Ensure automation window regains focus
        self.lift()
        self.focus_set()  
        # Set focus to search entry
    def recursive_search_with_filters(self, start_dir, search_term, extensions, date_limit, size_filter):
        results = []
        try:
            items = os.listdir(start_dir)
        except PermissionError:
            return results
        except Exception:
            return results

        for item in items:
            item_path = os.path.join(start_dir, item)
            try:
                # Skip if doesn't match search term
                if search_term.lower() not in item.lower():
                    # Still check subdirectories even if parent doesn't match
                    if os.path.isdir(item_path):
                        self.recursive_search_with_filters(item_path, search_term, extensions, date_limit, size_filter)
                    continue
                
                # Apply file type filter
                if extensions and os.path.isfile(item_path):
                    file_ext = os.path.splitext(item_path)[1].lower()
                    if file_ext not in extensions:
                        continue
                
                # Apply date filter
                if date_limit and os.path.exists(item_path):
                    mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    if mod_time < date_limit:
                        continue
                
                # Apply size filter
                if size_filter != "Any Size" and os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    if size_filter == "Small (<1MB)" and file_size >= 1024*1024:
                        continue
                    elif size_filter == "Medium (1-100MB)" and (file_size < 1024*1024 or file_size > 100*1024*1024):
                        continue
                    elif size_filter == "Large (>100MB)" and file_size <= 100*1024*1024:
                        continue
                
                # Item passed all filters, add to results
                self.add_search_result(item, item_path)
                self.local_results_found = True
                
                # Continue searching in subdirectories
                if os.path.isdir(item_path):
                    self.recursive_search_with_filters(item_path, search_term, extensions, date_limit, size_filter)
            except PermissionError:
                continue
            except Exception:
                continue
    def add_search_result(self, name, path):
        """Add an item to the search results tree"""
        try:
            # Determine file type
            if os.path.isdir(path):
                item_type = "Folder"
                icon = "📁"
                size_str = ""
            else:
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.txt', '.pdf', '.doc', '.docx', '.rtf']:
                    item_type = f"Document ({ext})"
                    icon = "📄"
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    item_type = f"Image ({ext})"
                    icon = "🖼️"
                elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                    item_type = f"Video ({ext})"
                    icon = "🎬"
                elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
                    item_type = f"Audio ({ext})"
                    icon = "🎵"
                else:
                    item_type = f"File ({ext})"
                    icon = "📄"
                
                # Format size
                size_bytes = os.path.getsize(path)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024*1024:
                    size_str = f"{size_bytes/1024:.1f} KB"
                elif size_bytes < 1024*1024*1024:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"
                else:
                    size_str = f"{size_bytes/(1024*1024*1024):.1f} GB"
            
            # Format date
            mod_time = datetime.fromtimestamp(os.path.getmtime(path))
            date_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Add to treeview
            self.search_tree.insert("", "end", text=icon, values=(name, path, item_type, size_str, date_str))
            self.search_tree.tag_configure('selected', background='#1a73e8')
            
        except Exception as e:
            pass

    def reset_search_filters(self):
        """Reset all search filters to defaults"""
        self.file_type_var.set("All Files")
        self.date_var.set("Any Time")
        self.size_var.set("Any Size")
        self.search_entry.delete(0, tk.END)
        
        # Clear results
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        self.results_count_label.config(text="Results: 0 items found")
        self.search_status.config(text="Filters reset")
    def on_search_double_click(self, event):
        try:
            item_id = self.search_tree.selection()[0]
        except IndexError:
            return
            
        item_values = self.search_tree.item(item_id, 'values')
        if item_values:
            item_path = item_values[1]
            if os.path.isfile(item_path):
                # Release grab before opening file
                self.grab_release()
                self.file_manager.open_file(item_path)
                # Re-grab after file is opened
                self.grab_set()
            elif os.path.isdir(item_path):
                self.navigate_to(item_path)
                # Close search window after navigating
                if self.search_results_window:
                    self.search_results_window.destroy()
                    self.search_results_window = None

    # def on_search_double_click(self, event):
    #     try:
    #         item_id = self.search_tree.selection()[0]
    #     except IndexError:
    #         return
            
    #     item_values = self.search_tree.item(item_id, 'values')
    #     if item_values:
    #         item_path = item_values[1]
    #         if os.path.isfile(item_path):
    #             # Release grab before opening file
    #             self.grab_release()
    #             self.file_manager.open_file(item_path)
    #             # Re-grab after file is opened
    #             self.grab_set()
    #         elif os.path.isdir(item_path):
    #             self.navigate_to(item_path)
    #             # Close search window after navigating
    #             if self.search_results_window:
    #                 self.search_results_window.destroy()
    #                 self.search_results_window = None

    def show_search_context_menu(self, event):
        item = self.search_tree.identify('item', event.x, event.y)
        if item:
            self.search_tree.selection_set(item)
            item_values = self.search_tree.item(item, 'values')
            
            if item_values:
                item_path = item_values[1]

                if not item_path:
                    return
                context_menu = Menu(self.parent, tearoff=0)
                
                # Add context menu items
                # Add cloud operations
                if 'cloud' in self.search_tree.item(item, 'tags'):
                    context_menu.add_command(label="Download from Cloud", 
                                        command=lambda: self.download_cloud_item(item_path))
                    context_menu.add_command(label="Share Cloud File",
                                        command=lambda: self.share_cloud_item(item_path))
                    context_menu.add_command(label="Delete from Cloud", command=lambda: self.delete_cloud_item(item_path))
                else:
                    context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))                
                    context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))                                
                    context_menu.add_command(label="Show in Folder", command=lambda: self.reveal_in_explorer(item_path))                
                context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
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
    # Search functionality 
    # def search_files(self):
    #     """Open search dialog"""
    #     search_term = simpledialog.askstring("Search", "Enter search term:")
    #     if search_term:
    #         # Store original directory to return to later
    #         original_dir = self.current_dir
            
    #         # Close any existing search window
    #         if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
    #             self.search_results_window.destroy()
                
    #         # Create new search results window
    #         self.search_results_window = tk.Toplevel(self)
    #         self.search_results_window.title("Search Results")
    #         self.search_results_window.geometry("600x400")
            
    #         self.search_tree = ttk.Treeview(self.search_results_window)
    #         self.search_tree.pack(expand=True, fill=tk.BOTH)
            
    #         # Configure columns
    #         self.search_tree["columns"] = ("path",)
    #         self.search_tree.column("#0", width=200, minwidth=200)
    #         self.search_tree.column("path", width=400, minwidth=200)
    #         self.search_tree.heading("#0", text="Name")
    #         self.search_tree.heading("path", text="Path")
            
    #         # Bind events
    #         self.search_tree.bind("<Button-3>", self.show_search_context_menu)
    #         self.search_tree.bind("<Double-1>", self.on_search_double_click)
            
    #         # Perform search
    #         self.recursive_search(self.automation_folder, search_term)
            
    #         # Return to original directory
    #         self.current_dir = original_dir
    #         self.update_file_list()

    # def recursive_search(self, start_dir, search_term, parent=""):
    #     """Search recursively for files/folders matching search term"""
    #     try:
    #         for item in os.listdir(start_dir):
    #             item_path = os.path.join(start_dir, item)
                
    #             if search_term.lower() in item.lower():
    #                 # Add icon based on item type
    #                 if os.path.isfile(item_path):
    #                     icon = "📄 "  # Document icon
    #                 else:
    #                     icon = "📁 "  # Folder icon
                        
    #                 self.search_tree.insert(parent, 'end', text=f"{icon}{item}", values=(item_path,), open=False)
                    
    #             if os.path.isdir(item_path):
    #                 self.recursive_search(item_path, search_term, parent)
    #     except Exception as e:
    #         pass  # Skip directories we can't access

    # def on_search_double_click(self, event):
    #     """Handle double click on search results"""
    #     try:
    #         item_id = self.search_tree.selection()[0]
    #     except IndexError:
    #         return
            
    #     item_values = self.search_tree.item(item_id, 'values')
    #     if item_values:
    #         item_path = item_values[0]
            
    #         if os.path.isfile(item_path):
    #             self.open_file(item_path)
    #         elif os.path.isdir(item_path):
    #             self.navigate_to(item_path)
    #             # Close search window
    #             self.search_results_window.destroy()

    # def show_search_context_menu(self, event):
    #     """Show context menu for search results"""
    #     item = self.search_tree.identify('item', event.x, event.y)
    #     if item:
    #         self.search_tree.selection_set(item)
    #         item_values = self.search_tree.item(item, 'values')
            
    #         if item_values and item_values[0]:
    #             item_path = item_values[0]
                
    #             context_menu = Menu(self, tearoff=0)
    #             context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
    #             context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
    #             context_menu.add_command(label="Show in Folder", 
    #                                    command=lambda: self.show_in_folder(item_path))
    #             context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                
    #             if os.path.isfile(item_path):
    #                 context_menu.add_separator()
    #                 context_menu.add_command(label="Classify This File", 
    #                                       command=lambda: self.classify_and_upload(item_path))
                                          
    #             context_menu.post(event.x_root, event.y_root)

    def show_in_folder(self, item_path):
        """Navigate to the folder containing the item and highlight it"""
        if not os.path.exists(item_path):
            messagebox.showerror("Error", "Path no longer exists")
            return
            
        # Navigate to parent folder
        if os.path.isfile(item_path):
            parent_dir = os.path.dirname(item_path)
            item_name = os.path.basename(item_path)
        else:
            parent_dir = os.path.dirname(os.path.normpath(item_path))
            item_name = os.path.basename(os.path.normpath(item_path))
            
        # Close search window
        if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
            self.search_results_window.destroy()
            
        # Set current directory and update view
        self.navigate_to(parent_dir)
        
        # Find and select the item
        for child in self.file_tree.get_children():
            item_text = self.file_tree.item(child, 'text')
            
            # Remove icon prefix if present
            if item_text.startswith(('📄 ', '📁 ', '🖼️ ', '🎬 ', '🎵 ')):
                item_text = item_text[2:]  # Skip icon and space
                
            if item_text == item_name:
                self.file_tree.selection_set(child)
                self.file_tree.focus(child)
                self.file_tree.see(child)  # Scroll to make visible
                break

    # AI automation features
    def upload_to_auto(self):
        """Upload a file for AI classification"""
        file_dialog = CustomFileDialog(self.parent, self.current_dir)
        self.parent.wait_window(file_dialog)
        
        selected_path = file_dialog.selected_file
        if not selected_path:
            return
            
        if not os.path.isfile(selected_path):
            messagebox.showerror("Error", "Please select a file, not a directory")
            return
            
        # Create necessary directory structure and classify the file
        self.classify_and_upload(selected_path)
        self.update_file_list()

    def classify_and_upload(self, selected_path):
        """Classify a file using AI and upload it to the appropriate folder"""
        if self.automation_folder in selected_path:
            messagebox.showinfo("Info", "File is already in the automation folder.")
            return
            
        try:
            file_name = os.path.basename(selected_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            dest_dir = self.automation_folder
            category_name = []
            
            # Processing based on file type
            if file_ext == '.txt':
                # Text file classification
                dest_dir = os.path.join(dest_dir, 'txt')
                category_map = {
                    0: 'legal',
                    1: 'literary',
                    2: 'technical'
                }
                
                try:
                    # Check if AI service is running
                    requests.get('http://10.145.65.74:8000/docs', timeout=2)
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
                        'http://10.145.65.74:8000/predict_txt',
                        files=files,
                        timeout=5
                    )
                    
                response.raise_for_status()
                category_idx = response.json()['category']
                category_name = [category_map.get(category_idx, 'unknown')]
                
            elif file_ext in ('.jpg', '.jpeg', '.png'):
                # Image file classification
                dest_dir = os.path.join(dest_dir, 'image')
                
                try:
                    # Check if AI service is running
                    requests.get('http://10.145.65.74:8002/docs', timeout=2)
                except requests.ConnectionError:
                    messagebox.showerror(
                        "AI Service Offline",
                        "Image classification unavailable\n"
                        "Start file_auto_img.py first"
                    )
                    return
                    
                # Get AI classification
                with open(selected_path, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(
                        'http://10.145.65.74:8002/predict_img',
                        files=files,
                        timeout=5
                    )
                    
                response.raise_for_status()
                category_list = response.json()['Top 5 predicted classes']
                
                # Determine categories based on confidence scores
                if category_list[0][0] > 0.6:
                    category_name = [category_list[0][1]]
                elif category_list[0][0] > 0.3 and category_list[1][0] > 0.2:
                    category_name = [category_list[0][1], category_list[1][1]]
                else:
                    category_name = ['unknown']

            elif file_ext in ('.pdf'):
                dest_dir = os.path.join(dest_dir, 'pdf')
                category_map = {
                    0: 'legal',
                    1: 'literary',
                    2: 'technical'
                }
                try:
                    requests.get('http://localhost:8000/docs', timeout=4)
                except requests.ConnectionError:
                    messagebox.showerror(
                        "AI Service Offline",
                        "Text classification unavailable\n"
                        "Start file_auto_txt.py first"
                    )
                    return

                # Get AI classification
                txt_from_pdf(selected_path, '__temp__.txt')

                with open('__temp__.txt', 'rb') as f:
                    files = {'file': f}
                    response = requests.post(
                        'http://localhost:8000/predict_txt',
                        files=files,
                        timeout=7
                    )
                    response.raise_for_status()
                    category_idx = response.json()['category']
                    category_name = [category_map.get(category_idx, 'unknown')]
                os.remove('__temp__.txt')

            else:
                messagebox.showerror(
                    "Unsupported Format",
                    f"Cannot process {file_ext} files\n"
                    "Supported formats: .txt, .jpg, .png"
                )
                return
                
            # Upload the file to the appropriate categories
            self.upload(dest_dir, file_name, file_ext, selected_path, category_name)
            
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

    def upload(self, dest_dir, file_name, file_ext, selected_path, category_name):
        """Upload a file to the specified destination after classification"""
        if not category_name:
            return
            
        success = []
        temp = dest_dir
        
        for category in category_name:
            dest_dir = temp
            dest_dir = os.path.join(dest_dir, category)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Generate unique filename
            base_name = os.path.splitext(file_name)[0]
            final_name = file_name
            counter = 1
            
            while os.path.exists(os.path.join(dest_dir, final_name)):
                final_name = f"{base_name}_{counter}{file_ext}"
                counter += 1
                
            dest_path = os.path.join(dest_dir, final_name)
            
            # Perform the file copy
            try:
                shutil.copy2(selected_path, dest_path)
                self.update_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Could not upload item: {e}")
                return
                
            # Log the action
            log_action(self.username, 'AUTO_UPLOAD', 'FILE', 
                     f"{selected_path} → {dest_path}", f"classified as {category}")
                     
            # Prepare success message
            success_msg = (f"Moved to: {os.path.relpath(dest_path, self.automation_folder)}\n"
                         f"Location: {dest_path}")
            success_msg = (f"Classified as {category}\n" + success_msg)
            success.append(success_msg)
            
        # Update status and show success message
        self.update_status(f"File classified and uploaded as: {', '.join(category_name)}")
        
        # Refresh if in automation directory
        if compare_path(self.current_dir, self.automation_folder):
            self.update_file_list()
            
        messagebox.showinfo("Success", "\n".join(success))

    def return_auto_folder(self):
        """Return the automation folder path to the parent"""
        return self.automation_folder
