import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk, Menu
import os
import sqlite3
import time
import subprocess
from newfilemanager import FileManager, allow_access, restrict_access
from automation import AutomationWindow
from utility import CustomDirectoryDialog, compare_path
from database import log_action, get_user_logs
from cloud import CloudManager

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

class LogViewer(tk.Toplevel):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.title("Activity Logs")
        self.tree = ttk.Treeview(self, columns=('Time', 'Action', 'Type', 'Path', 'Details'))
        
        self.tree.heading('#0', text='ID')
        self.tree.column('#0', width=50)
        for col in ('Time', 'Action', 'Type', 'Path', 'Details'):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        logs = get_user_logs(username)
        for log in logs:
            self.tree.insert('', 'end', values=log)
        
        self.tree.pack(expand=True, fill='both')

class FileManagerGUI:
    def __init__(self, username):
        self.root = tk.Tk()
        self.root.title("DocuVault: Secure Desktop File Manager")
        self.root.geometry("800x400")
        
        try:
            self.root.iconbitmap(r"AppIcon\DocuVault-icon.ico")
        except Exception:
            pass
        
        self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')
        os.makedirs(self.bin_dir, exist_ok=True)
        restrict_access(self.bin_dir)
        
        self.search_results_window = None
        self.cloud = None
        self.progress_window = None
        
        choice = messagebox.askyesno("Directory Choice", "Do you want to start in the current directory?")
        self.current_dir = os.getcwd() if choice else os.path.expanduser('~')
        self.original_dir = self.current_dir
        
        self.username = username
        self.file_manager = FileManager(username, self.bin_dir)
        self.automation_folder = self.file_manager.automation_folder
        
        self.create_widgets()
        self.update_file_list()
        self.root.after(100, self.initialize_cloud)

    def initialize_cloud(self):
        self.cloud = CloudManager(self.username, gui_callback=self)
        self.update_cloud_status('disconnected')

    def create_widgets(self):
        style = ttk.Style()
        try:
            style.theme_use('vista' if os.name == 'nt' else 'clam')
        except tk.TclError:
            style.theme_use('default')
        
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        nav_frame = ttk.Frame(top_frame)
        nav_frame.pack(side=tk.LEFT)
        
        nav_buttons = [
            ("↩️", self.go_to_parent_directory, "Back"),
            ("🏠", self.go_to_root, "Home"),
            ("💻", self.go_to_desktop, "Desktop"),
            ("🔄", self.update_file_list, "Refresh"),
            ("🔍", self.search_files, "Search")
        ]
        
        for emoji, command, tooltip_text in nav_buttons:
            btn = ttk.Button(nav_frame, text=emoji, width=2, command=command)
            btn.pack(side=tk.LEFT, padx=2)
            Tooltip(btn, tooltip_text)
        
        # Path section (center)
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.path_label = ttk.Label(path_frame, text=self.current_dir)
        self.path_label.pack(side=tk.LEFT)
        
        # Cloud controls (right)
        cloud_frame = ttk.Frame(top_frame)
        cloud_frame.pack(side=tk.RIGHT)
        
        # Cloud status indicator
        self.cloud_status = ttk.Label(cloud_frame, text="💭", font=("Arial", 12))
        self.cloud_status.pack(side=tk.RIGHT, padx=5)
        
        # Connect to cloud button
        self.connect_cloud_button = ttk.Button(cloud_frame, text="Connect",
                                               command=self.connect_to_cloud)
        self.connect_cloud_button.pack(side=tk.RIGHT, padx=5)
        
        # Cloud setup button
        cloud_setup_btn = ttk.Button(cloud_frame, text="💭 Setup",
                                     command=self.setup_cloud_config)
        cloud_setup_btn.pack(side=tk.RIGHT, padx=2)
        
        # Second toolbar for file operations
        toolbar_frame = ttk.Frame(self.root)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Left section: New dropdown
        left_section = ttk.Frame(toolbar_frame)
        left_section.pack(side=tk.LEFT)
        
        # New dropdown button
        new_btn = ttk.Button(left_section, text="New 🔽")
        new_btn.pack(side=tk.LEFT, padx=2)
        
        # New dropdown menu
        new_menu = tk.Menu(self.root, tearoff=0)
        new_menu.add_command(label="File", command=self.create_file)
        new_menu.add_command(label="Folder", command=self.create_folder)
        
        def show_new_menu(event=None):
            x = new_btn.winfo_rootx()
            y = new_btn.winfo_rooty() + new_btn.winfo_height()
            new_menu.post(x, y)
        
        new_btn.config(command=show_new_menu)

        # Center section: File operations
        self.center_section = ttk.Frame(toolbar_frame)
        self.center_section.pack(side=tk.LEFT, padx=20)
        
        # Use the new update_toolbar_buttons method instead of direct button creation
        self.update_toolbar_buttons()
        
        # Right section: Special operations
        right_section = ttk.Frame(toolbar_frame)
        right_section.pack(side=tk.RIGHT)
        
        # Automation window button
        self.automation_button = ttk.Button(right_section, text="⚙️ Automation",
                                            command=self.open_automation_window)
        self.automation_button.pack(side=tk.RIGHT, padx=2)
        
        # User Log View Button
        self.log_button = ttk.Button(right_section, text="Activity Log", command=self.show_activity_log)
        self.log_button.pack(side=tk.RIGHT, padx=2)
        
        # Cloud search button
        cloud_search_btn = ttk.Button(right_section, text="💭 Search",
                                      command=self.search_cloud_files)
        cloud_search_btn.pack(side=tk.RIGHT, padx=2)
        
        # Create a frame for the file tree and scrollbar
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # File tree (main content)
        self.file_tree = ttk.Treeview(tree_frame, selectmode="extended")
        self.file_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.file_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.configure(yscrollcommand=vsb.set)
        
        # Set up event bindings
        self.root.bind('<Control-a>', self.select_all)
        self.file_tree.bind('<Control-a>', self.select_all)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        self.file_tree.bind("<Button-3>", self.show_context_menu)
        self.file_tree.bind("<Button-1>", self.deselect_on_empty_space, add="+")

    def update_toolbar_buttons(self):
        for widget in self.center_section.winfo_children():
            widget.destroy()
        
        if (os.path.basename(self.bin_dir) in os.path.normpath(self.current_dir).split(os.path.sep)):
            operations = [
                ("Delete", self.delete_item),
                ("♻️ Restore", self.restore_item),
                ("🗑 Empty Bin", self.empty_bin)
            ]
        else:
            operations = [
                ("Move", self.move_item),
                ("Copy", self.copy_item),
                ("Delete", self.delete_item),
                ("🗑 Open Bin", self.go_to_bin)
            ]
        
        for text, command in operations:
            btn = ttk.Button(self.center_section, text=text, command=command)
            btn.pack(side=tk.LEFT, padx=2)

    def select_all(self, event=None):
        for item in self.file_tree.get_children():
            self.file_tree.selection_add(item)
        return "break"

    def go_to_root(self):
        if self.current_dir == self.bin_dir:
            restrict_access(self.bin_dir)
        self.current_dir = os.path.expanduser('~')
        self.update_file_list()

    def go_to_desktop(self):
        if self.current_dir == self.bin_dir:
            restrict_access(self.bin_dir)
        desktop_path = os.path.join(os.path.expanduser('~'), r'OneDrive\Desktop')
        if os.path.exists(desktop_path):
            self.current_dir = desktop_path
            self.update_file_list()
        else:
            messagebox.showinfo("Info", "Desktop directory not found.")

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
            
            self.local_results_found = False
            results, _ = self.file_manager.recursive_search(self.current_dir, search_term)
            
            for item, item_path in results:
                self.search_tree.insert("", "end", text=item, values=(item_path,))
                self.local_results_found = True
            
            if not self.local_results_found:
                self.search_tree.insert("", "end", text="No matching local records", values=("",))
            
            self.current_dir = original_dir
            self.update_file_list()
            
            if messagebox.askyesno("Cloud Search", "Search in Nextcloud storage?"):
                if self.cloud and self.cloud.nc:
                    self.cloud.search_files(search_term, callback=self.display_cloud_results)
                else:
                    messagebox.showinfo("Cloud Search", "Please connect to cloud first")
            
            self.search_results_window.lift()
            self.search_results_window.focus_set()

    def on_search_double_click(self, event):
        item_id = self.search_tree.selection()[0]
        item_values = self.search_tree.item(item_id, 'values')
        if item_values:
            item_path = item_values[0]
            if os.path.isfile(item_path):
                self.file_manager.open_file(item_path)
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

                if not item_path:
                    return
                context_menu = Menu(self.root, tearoff=0)
                
                # Add context menu items
                # Add cloud operations
                if 'cloud' in self.search_tree.item(item, 'tags'):
                    context_menu.add_command(label="Download from Cloud", 
                                        command=lambda: self.download_cloud_item(item_path))
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
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

    def update_file_list(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        self.populate_tree(self.file_tree, self.current_dir)
        self.path_label.config(text=self.current_dir)

        # Update toolbar buttons whenever directory changes
        self.update_toolbar_buttons()

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
                self.file_manager.open_file(item_path)
            elif item_type == 'folder':
                self.go_into_directory(item_path)

    def show_context_menu(self, event):
        """Show context menu for file/folder or empty space"""
        # Identify the item that was right-clicked
        clicked_item = self.file_tree.identify('item', event.x, event.y)        
        if clicked_item:
            # Check if the clicked item is already selected
            current_selection = self.file_tree.selection()            
            # If clicked item is not in current selection, make it the only selection
            if clicked_item not in current_selection:
                self.file_tree.selection_set(clicked_item)
            # Otherwise keep the current multiple selection
            
            # Now get the item values of the clicked item
            item_values = self.file_tree.item(clicked_item, 'values')            
            if item_values:
                item_type, item_path = item_values                
                context_menu = Menu(self.root, tearoff=0)                
                if (os.path.basename(self.bin_dir) in os.path.normpath(self.current_dir).split(os.path.sep)):
                    context_menu.add_command(label="Restore", command=lambda: self.restore_item())
                    context_menu.add_command(label="Delete", command=lambda: self.delete_item())
                    context_menu.add_command(label="Empty Bin", command=lambda: self.empty_bin())
                    context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                else:
                    context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
                    context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
                    context_menu.add_command(label="Rename", command=lambda: self.rename_item(item_path))
                    context_menu.add_command(label="Copy", command=lambda: self.copy_item())
                    context_menu.add_command(label="Move", command=lambda: self.move_item())
                    context_menu.add_command(label="Delete", command=lambda: self.delete_item())
                    context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                    context_menu.add_command(label="Upload to Cloud", 
                                            command=lambda: self.upload_to_cloud(item_path))
                
                context_menu.tk_popup(event.x_root, event.y_root)
        else:
            # Clicked on empty space
            context_menu = Menu(self.root, tearoff=0)
            context_menu.add_command(label="Create File", command=self.create_file)
            context_menu.add_command(label="Create Folder", command=self.create_folder)
            context_menu.add_command(label="Refresh", command=self.update_file_list)
            
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
            self.file_tree.selection_set([])  # Alternative way to clear
            self.file_tree.focus("")  # Clear focus as well
            return "break"

    def go_into_directory(self, path):
        if os.path.isdir(path):
            try:
                # Attempt to list the contents of the directory
                os.listdir(path)
                # If successful, update current_dir and file list
                self.current_dir = path
                self.update_file_list()
            except PermissionError:
                messagebox.showwarning("Access Denied", f"Permission denied for directory:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not access directory: {str(e)}")

    def go_to_parent_directory(self):
        if self.current_dir == self.bin_dir:
            messagebox.showinfo("Bin Directory","You are currently in the DocuVault Bin.\n\nClick on Home/Desktop to get out of Bin.")
            return
        if self.current_dir != os.path.expanduser("~"):
            self.current_dir = os.path.dirname(self.current_dir)
            self.update_file_list()
        else:
            messagebox.showinfo("Home Directory", "You are already at the home directory.")

    def go_to_bin(self):
        allow_access(self.bin_dir)
        self.current_dir = self.bin_dir
        self.update_file_list()

    def copy_path(self, item_path):
        """Copy file/folder path to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(item_path)

    def create_file(self):
        filename = simpledialog.askstring("Create File", "Enter file name:")
        success, message = self.file_manager.create_file(self.current_dir, filename)
        if success:
            self.update_file_list()
        else:
            messagebox.showerror("Error", message)

    def create_folder(self):
        foldername = simpledialog.askstring("Create Folder", "Enter folder name:")
        success, message = self.file_manager.create_folder(self.current_dir, foldername)
        if success:
            self.update_file_list()
        else:
            messagebox.showerror("Error", message)

    def rename_item(self, item_path):
        old_name = os.path.basename(item_path)
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=old_name)
        if new_name and new_name != old_name:
            success, message = self.file_manager.rename_item(item_path, new_name)
            if success:
                self.update_file_list()
            else:
                messagebox.showerror("Error", message)

    def delete_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_delete = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        if (os.path.basename(self.bin_dir) in os.path.normpath(self.current_dir).split(os.path.sep)):
            confirm = messagebox.askyesno("Confirm Permanent Deletion", "Are you sure you want to permanently delete the selected items?")
            if confirm:
                result = self.file_manager.delete_item(self.current_dir, items_to_delete, permanently=True)
            else:
                return
        else:
            response = messagebox.askyesnocancel("Delete Items",
                f"What would you like to do with the selected item(s)?\n\nYes = Delete permanently\nNo = Move to Bin\nCancel = Abort operation")
            if response is None:  # Cancel
                return
            if response:
                result = self.file_manager.delete_item(self.current_dir, items_to_delete, permanently=True)
            else:
                result = self.file_manager.delete_item(self.current_dir, items_to_delete)
        
        if result["success_count"] > 0:
            messagebox.showinfo("Success", f"Successfully deleted {result['success_count']} item(s)")
        
        if result["failed_items"]:
            failed_msg = "\n".join(result["failed_items"])
            messagebox.showerror("Error", f"Failed to delete some items:\n{failed_msg}")
        
        if result["skipped_items"]:
            skipped_msg = "\n".join(result["skipped_items"])
            messagebox.showinfo("Info", f"Skipped items:\n{skipped_msg}")
        self.update_file_list()

    def move_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_move = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)  # Wait for dialog to close
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.move_item(items_to_move, destination)
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
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_copy = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)  # Wait for dialog to close
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.copy_item(items_to_copy, destination)
            if result["success_count"] > 0:
                messagebox.showinfo("Success", f"Successfully copied {result['success_count']} item(s) to {result['destination']}")
            
            if result["failed_items"]:
                failed_msg = "\n".join(result["failed_items"])
                messagebox.showerror("Error", f"Failed to copy some items:\n{failed_msg}")
        self.update_file_list()

    def empty_bin(self):
        confirm = messagebox.askyesno("Confirm Empty Bin", "Are you sure you want to permanently delete all items in the Bin?")
        if confirm:
            result = self.file_manager.empty_bin()
            if isinstance(result, dict):
                if result["success_count"] > 0:
                    messagebox.showinfo("Success", f"Successfully deleted {result['success_count']} item(s) from the Bin")
                if result["failed_items"]:
                    failed_msg = "\n".join(result["failed_items"])
                    messagebox.showerror("Error", f"Failed to delete some items:\n{failed_msg}")
            else:
                messagebox.showinfo("Info", result)
        self.update_file_list()

    def restore_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_restore = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)
        
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.restore_item(items_to_restore, destination)
            if result["success_count"] > 0:
                messagebox.showinfo("Success", f"Successfully restored {result['success_count']} item(s) to {result['destination']}")
            
            if result["failed_items"]:
                failed_msg = "\n".join(result["failed_items"])
                messagebox.showerror("Error", f"Failed to restore some items:\n{failed_msg}")
        self.update_file_list()

    def open_file(self, item_path):
        if os.path.isfile(item_path):
            success, message = self.file_manager.open_file(item_path)
            if not success:
                messagebox.showerror("Error", message)
        elif os.path.isdir(item_path):
            self.go_into_directory(item_path)
        else:
            messagebox.showinfo("Info", "Selected item cannot be opened")

    def open_with(self, item_path):
        available_apps = self.file_manager.get_available_apps(item_path)
        if not available_apps:
            messagebox.showinfo("Info", "No applications found to open this file")
            return
        
        app_window = tk.Toplevel(self.root)
        app_window.title("Open With")
        app_window.geometry("400x300")
        
        listbox = tk.Listbox(app_window)
        listbox.pack(expand=True, fill=tk.BOTH)
        
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

    def show_activity_log(self):
        LogViewer(self.root, self.username)

    ##############################
    # Automation Callbacks       #
    ##############################
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

    ##############################
    # Cloud Operations Callbacks #
    ##############################
    def connect_to_cloud(self):
        """Initiate connection to the cloud"""
        if self.cloud and self.cloud.nc:
            messagebox.showinfo("Cloud Info", "Already connected to cloud")
            return            
        if not self.cloud:
            self.initialize_cloud()
        else:
            # Re-attempt connection with existing cloud manager
            self.root.after(0, lambda: self.cloud._load_credentials())

    def update_cloud_status(self, status):
        """Update the cloud status indicator
        status: 'connected', 'disconnected', 'failed'
        """
        if status == 'connected':
            self.cloud_status.config(text="💭✅", foreground="green")
            self.connect_cloud_button.config(text="Cloud Connected")
        elif status == 'disconnected':
            self.cloud_status.config(text="💭", foreground="gray")
            self.connect_cloud_button.config(text="Connect to Cloud")
        elif status == 'failed':
            self.cloud_status.config(text="💭❌", foreground="red")
            self.connect_cloud_button.config(text="Reconnect")

    def setup_cloud_config(self):
        config_win = tk.Toplevel(self.root)
        config_win.title("Cloud Configuration")
        config_win.geometry("300x200")

        entries = [
            ("Server URL", "server_url"),
            ("Username", "cloud_user"),
            ("Password", "cloud_pass")
        ]
        entry_widgets = {}
        for label, field_name in entries:
            ttk.Label(config_win, text=label).pack()
            entry = ttk.Entry(config_win)
            entry.pack(pady=5)
            entry_widgets[field_name] = entry
        
        def save_config():
            url=entry_widgets["server_url"].get()
            user=entry_widgets["cloud_user"].get()
            password=entry_widgets["cloud_pass"].get()

            if not url or not user or not password:
                messagebox.showerror("Error", "Please fill in all fields")
                return
            self.cloud.store_credentials(
                server_url=url,
                cloud_user=user,
                cloud_pass=password,
                master_password=self.get_master_password()
            )
            config_win.destroy()
        
        ttk.Button(config_win, text="Save", command=save_config).pack(pady=10)

    def get_master_password(self):
        return simpledialog.askstring("Security Check",
                                      "Enter your master password for auto-connecting to cloud:",
                                      show='*')

    def show_progress(self, message):
        if self.progress_window and tk.Toplevel.winfo_exists(self.progress_window):
            self.progress_window.destroy()
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Cloud Operation Progress")
        self.progress_label = tk.Label(self.progress_window, text=message)
        self.progress_label.pack()
        self.progress_bar = ttk.Progressbar(self.progress_window, orient="horizontal",
                                            length=300, mode="determinate")
        self.progress_bar.pack()

    def update_progress(self, value, message=None):
        if message:
            self.progress_label.config(text=message)
        self.progress_bar['value'] = value
        if value >= 100 and message:
            if "Connected to Nextcloud" in message:
                self.update_cloud_status('connected')
            self.progress_window.after(2000, self.progress_window.destroy)

    def delete_cloud_item(self, cloud_path):
        remote_path = f"/DocuVault/{os.path.basename(cloud_path)}"
        if messagebox.askyesno("Confirm", "Delete from cloud?"):
            self.cloud.delete_file(remote_path)

    def show_error(self, message):
        messagebox.showerror("Cloud Error", message)
        if "Connection failed" in message:
            self.update_cloud_status('failed')
        if hasattr(self, 'progress_window') and self.progress_window and tk.Toplevel.winfo_exists(self.progress_window):
            self.progress_window.destroy()

    def show_info(self, message):
        messagebox.showinfo("Cloud Info", message)

    def display_cloud_results(self, results):
        if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
            self.search_tree.tag_configure(tagname='cloud', foreground='blue')
            if not results or len(results) == 0:
                self.search_tree.insert("", "end",
                                        text="No matching cloud records",
                                        values=("",),
                                        tags=('cloud',))
                return
            for item in results:
                self.search_tree.insert("", "end",
                                        text=item.name,
                                        values=(f"Cloud: {item.user_path}",),
                                        tags=('cloud',))

    def search_cloud_files(self):
        search_term = simpledialog.askstring("Cloud Search", "Enter search term:")
        if search_term:
            if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
                self.search_results_window.destroy()
            self.search_results_window = tk.Toplevel(self.root)
            self.search_results_window.title("Cloud Search Results")
            self.search_results_window.geometry("600x400")
            self.search_tree = ttk.Treeview(self.search_results_window)
            self.search_tree.pack(expand=True, fill=tk.BOTH)
            self.search_tree["columns"] = ("path",)
            self.search_tree.column("#0", width=200, minwidth=200)
            self.search_tree.column("path", width=400, minwidth=200)
            self.search_tree.heading("#0", text="Name")
            self.search_tree.heading("path", text="Path")
            self.search_tree.bind("<Button-3>", self.show_search_context_menu)
            self.search_tree.bind("<Control-1>", self.show_search_context_menu)  # For macOS
            self.search_tree.bind("<Double-1>", self.on_search_double_click)
            if self.cloud and self.cloud.nc:
                self.cloud.search_files(search_term, callback=self.display_cloud_results)
            else:
                messagebox.showinfo("Cloud Search", "Please connect to cloud first")
                self.search_results_window.destroy()

    def download_cloud_item(self, cloud_path):
        filename = os.path.basename(cloud_path)
        remote_path = f"/DocuVault/{filename}"
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)
        if dest_dialog.selected_path:
            dest_dir = dest_dialog.selected_path
            local_path = os.path.join(dest_dir, filename)
            if os.path.exists(local_path):
                overwrite = messagebox.askyesno(
                    "File Already Exists",
                    f"The file '{filename}' already exists in the destination folder.\n\nDo you want to overwrite it?"
                )
                if not overwrite:
                    rename = messagebox.askyesno(
                        "Rename File",
                        "Do you want to rename the downloading file?"
                    )
                    if rename:
                        new_name = simpledialog.askstring(
                            "Rename File",
                            "Enter a new name for the file:"
                        )
                        if not new_name:
                            messagebox.showinfo("Info", "Download canceled")
                            return
                        file_ext = os.path.splitext(filename)[1]
                        if not new_name.endswith(file_ext):
                            new_name += file_ext
                        new_path = os.path.join(dest_dir, new_name)
                        if os.path.exists(new_path):
                            messagebox.showerror("Error", f"A file named '{new_name}' also exists. Download aborted.")
                            return
                        self.cloud.download_file(
                            remote_path=remote_path,
                            local_dir=dest_dir,
                            custom_local_path=new_path
                        )
                        return
                    else:
                        messagebox.showinfo("Info", "Download canceled")
                        return
            self.cloud.download_file(
                remote_path=remote_path,
                local_dir=dest_dir
            )

    def upload_to_cloud(self, local_path):
        if os.path.isdir(local_path):
            messagebox.showinfo("Cloud Upload", "Folder can't be uploaded. Please select a file.")
            return
        if self.cloud and self.cloud.nc:
            self.cloud.upload_file(local_path, f"/DocuVault/{os.path.basename(local_path)}")
        else:
            messagebox.showinfo("Cloud Upload", "Please connect to cloud first")

    def run(self):
        self.root.mainloop()
