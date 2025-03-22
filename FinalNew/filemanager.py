import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import stat
import shutil
import sqlite3
import subprocess
from tkinter import ttk  # For the Treeview widget
from tkinter import Menu
from automation import AutomationWindow
from utility import CustomDirectoryDialog, compare_path
from database import log_action, get_user_logs
from cloud import CloudManager
from datetime import datetime

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
        
        # Create a toplevel window
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

def remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)  # Remove read-only flag
        func(path)


class LogViewer(tk.Toplevel):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.title("Activity Logs")
        self.tree = ttk.Treeview(self, columns=('Time', 'Action', 'Type', 'Path', 'Details'))
        
        # Configure columns
        self.tree.heading('#0', text='ID')
        self.tree.column('#0', width=50)
        for col in ('Time', 'Action', 'Type', 'Path', 'Details'):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
            
        # Populate logs
        logs = get_user_logs(username)
        for log in logs:
            self.tree.insert('', 'end', values=log)
            
        self.tree.pack(expand=True, fill='both')


class FileManagerGUI:
    def __init__(self, username):
        self.root = tk.Tk()
        # self.root.iconbitmap("AppIcon\\DocuVault-icon.ico")
        self.root.title("DocuVault: Secure Desktop File Manager")
        self.root.geometry("800x400")
        self.sort_by = "name"  # Default sorting criterion
        # Set application icon
        try:
            self.root.iconbitmap("AppIcon\\Docu-icon.ico")
        except Exception as e:
            pass
        self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')
        os.makedirs(self.bin_dir, exist_ok=True)
        self.search_results_window = None
        
        self.cloud = None  # Placeholder for cloud manager
        self.progress_window = None

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

        # Delay cloud initialization until the window is mapped.
        self.root.after(100, self.initialize_cloud)

    def initialize_cloud(self):
        self.cloud = CloudManager(self.username, gui_callback=self)
        self.update_cloud_status('disconnected')

####################################################################################################
# Modern File Manager GUI widgets
    def create_widgets(self):
        # Apply a modern theme with ttk
        style = ttk.Style()
        try:
            # Try platform-specific themes first
            if os.name == 'nt':  # Windows
                style.theme_use('vista')
            else:  # Unix/Mac
                style.theme_use('clam')
        except tk.TclError:
            # Fallback to default
            style.theme_use('default')
        
        # Main top frame for navigation and path
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation section (left)
        nav_frame = ttk.Frame(top_frame)
        nav_frame.pack(side=tk.LEFT)
        
        # Navigation buttons with emojis
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
            Tooltip(btn, tooltip_text)  # Add tooltip
        
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
        cloud_setup_btn = ttk.Button(cloud_frame, text="💭 Search", 
                                    command=self.search_cloud_files)
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

        # Create Sort button with dropdown
        sort_btn = ttk.Button(left_section, text="Sort 🔽")
        sort_btn.pack(side=tk.LEFT, padx=2)

        # Sort dropdown menu
        sort_menu = tk.Menu(self.root, tearoff=0)

        # Define sorting functions
        def sort_by_name():
            self.sort_by = "name"
            self.update_file_list()  

        def sort_by_date():
            self.sort_by = "date"
            self.update_file_list()

        def sort_by_size():
            self.sort_by = "size"
            self.update_file_list()

        # Add menu options
        sort_menu.add_command(label="Name", command=sort_by_name)
        sort_menu.add_command(label="Date", command=sort_by_date)
        sort_menu.add_command(label="Size", command=sort_by_size)

        # Function to show the dropdown menu
        def show_sort_menu(event=None):
            x = sort_btn.winfo_rootx()
            y = sort_btn.winfo_rooty() + sort_btn.winfo_height()
            sort_menu.post(x, y)

        # Configure button to show menu when clicked
        sort_btn.config(command=show_sort_menu)
        
        # Center section: File operations
        self.center_section = ttk.Frame(toolbar_frame)
        self.center_section.pack(side=tk.LEFT, padx=20)

        # Use the new update_toolbar_buttons method instead of direct button creation
        self.update_toolbar_buttons()
        
        # Right section: Special operations
        right_section = ttk.Frame(toolbar_frame)
        right_section.pack(side=tk.RIGHT)

        # Add Settings button - place it before the other buttons
        self.settings_button = ttk.Button(right_section, text="⚙️ Settings", 
                                        command=self.show_settings_dialog)
        self.settings_button.pack(side=tk.RIGHT, padx=2)

        # Activity Log button - Added here with consistent styling and an appropriate icon
        self.log_button = ttk.Button(right_section, text="📋 Activity Log", command=self.show_activity_log)
        self.log_button.pack(side=tk.RIGHT, padx=2)
        
        # Automation window button
        self.automation_button = ttk.Button(right_section, text="⚙️ Automation", 
                                        command=self.open_automation_window)
        self.automation_button.pack(side=tk.RIGHT, padx=2)
        
        # Cloud search button
        cloud_search_btn = ttk.Button(right_section, text="💭 Setup", 
                                    command=self.show_cloud_config)
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
        self.file_tree.bind("<ButtonRelease-1>", self.deselect_on_empty_space, add="+")
        
    def show_settings_dialog(self):
        """Open a dialog with user settings including account deletion option"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("DocuVault Settings")
        settings_window.geometry("450x350")
        settings_window.resizable(False, False)
        
        # Create main container with padding
        settings_frame = ttk.Frame(settings_window, padding=15)
        settings_frame.pack(fill="both", expand=True)
        
        # Add header
        header_label = ttk.Label(settings_frame, text="User Settings", 
                            font=("Segoe UI", 14, "bold"))
        header_label.pack(pady=(0, 15))
        
        # User information section
        info_section = ttk.LabelFrame(settings_frame, text="Account Information")
        info_section.pack(fill="x", pady=10, padx=5)
        
        username_label = ttk.Label(info_section, text=f"Username: {self.username}")
        username_label.pack(anchor="w", pady=5, padx=5)
        
        # Call the method to create the delete account section
        self.create_settings_frame(settings_frame)
        
        # Close button at bottom
        close_button = ttk.Button(settings_frame, text="Close", 
                                command=settings_window.destroy)
        close_button.pack(pady=15)

    def create_settings_frame(self, settings_frame):
        """Create settings sections including sign out and delete account"""
        
        # Add Sign Out section
        session_section = ttk.LabelFrame(settings_frame, text="Session Management")
        session_section.pack(fill="x", pady=10, padx=5)
        
        signout_button = ttk.Button(session_section, text="Sign Out", 
                command=self.sign_out, style="Accent.TButton"
        )
        signout_button.pack(pady=5)
        
        # Add Delete Account section
        delete_section = ttk.LabelFrame(settings_frame, text="Delete Account")
        delete_section.pack(fill="x", pady=10, padx=5)
        
        delete_warning = ttk.Label(delete_section,
            text="Warning: This will permanently delete your account and all associated data.")
        delete_warning.pack(pady=5)
        
        delete_button = ttk.Button(delete_section, text="Delete Account",
            style="Accent.TButton", command=self.confirm_delete_account)
        delete_button.pack(pady=10)

    def confirm_delete_account(self):
        """Handle account deletion after confirmation"""
        confirm = messagebox.askyesno("Confirm Deletion", 
            "Are you sure you want to delete your account? This action cannot be undone.")
        
        if confirm:
            # Double-confirm with password for security
            password = simpledialog.askstring("Security Check", 
                "Please enter your password to confirm deletion:", show='*')
            
            if password:
                from database import delete_user_account, login_user
                
                # Verify password first
                if login_user(self.username, password):
                    if delete_user_account(self.username):
                        messagebox.showinfo("Account Deleted", 
                            "Your account has been successfully deleted.")
                        self.root.destroy()
                        from login import LoginPage
                        login_page = LoginPage()
                        login_page.mainloop()
                    else:
                        messagebox.showerror("Error", 
                            "There was a problem deleting your account. Please try again.")
                else:
                    messagebox.showerror("Authentication Failed", 
                        "Incorrect password. Account deletion cancelled.")

    def sign_out(self):
        """Handle sign out process"""
        confirm = messagebox.askyesno("Confirm Sign Out", 
            "Are you sure you want to sign out?")
        
        if confirm:
            self.root.destroy()
            from login import LoginPage
            login_page = LoginPage()
            login_page.mainloop()

    def update_toolbar_buttons(self):
        # Clear all existing buttons from center section
        for widget in self.center_section.winfo_children():
            widget.destroy()
        
        # Set up buttons based on current directory
        if self.current_dir == self.bin_dir:
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
        """Select all items in the current view"""
        for item in self.file_tree.get_children():
            self.file_tree.selection_add(item)
        return "break"  # Prevents default behavior

    def go_to_root(self):
        self.current_dir = os.path.expanduser('~')
        self.update_file_list()

    def go_to_desktop(self):
        """Navigate to the desktop directory"""
        desktop_path = os.path.join(os.path.expanduser('~'), 'OneDrive\\Desktop')
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


            # Track if any local results were found
            self.local_results_found = False
            self.recursive_search(self.current_dir, search_term, "")
            # Display message if no local results found
            if not self.local_results_found:
                self.search_tree.insert("", "end", text="No matching local records", values=("",))
            self.current_dir = original_dir
            self.update_file_list()

            # Add cloud search
            if messagebox.askyesno("Cloud Search", "Search in Nextcloud storage?"):
                if self.cloud and self.cloud.nc:
                    self.cloud.search_files(
                        search_term,
                        callback=self.display_cloud_results
                    )
                else:
                    messagebox.showinfo("Cloud Search", "Please connect to cloud first")
            # Bring search window back to focus after dialog
            self.search_results_window.lift()
            self.search_results_window.focus_set()

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
                    self.local_results_found = True  # Mark that we found at least one result
                    
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
            
            # Sort items based on the selected criteria
            if self.sort_by == "name":
                items = sorted(items)
            elif self.sort_by == "size":
                items = sorted(items, key=lambda item: os.path.getsize(os.path.join(directory, item)))
            elif self.sort_by == "date":
                items = sorted(items, key=lambda item: os.path.getmtime(os.path.join(directory, item)))

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
                if self.current_dir == self.bin_dir:
                    context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
                    context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
                    context_menu.add_command(label="Rename", command=lambda: self.rename_item(clicked_item))
                    context_menu.add_command(label="Restore", command=lambda: self.restore_item())
                    context_menu.add_command(label="Delete", command=lambda: self.delete_item())
                    context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                else:
                    context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
                    context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
                    context_menu.add_command(label="Rename", command=lambda: self.rename_item(clicked_item))
                    context_menu.add_command(label="Copy", command=lambda: self.copy_item())
                    context_menu.add_command(label="Move", command=lambda: self.move_item())
                    context_menu.add_command(label="Delete", command=lambda: self.delete_item())
                    context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                    context_menu.add_command(label="Upload to Cloud", 
                                            command=lambda: self.upload_to_cloud(item_path))
                context_menu.add_command(label="Metadata", command=self.show_metadata)  # New metadata option 
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

    def show_metadata(self):
        """Display file/folder metadata in a new window"""
        try:
            clicked_item = self.file_tree.selection()[0]
            item_values = self.file_tree.item(clicked_item, 'values')
            if item_values:
                item_type, item_path = item_values
                if item_type in ('file', 'folder'):
                    metadata = self.get_metadata(item_path)
                    metadata_window = tk.Toplevel(self.root)
                    metadata_window.title(f"Metadata - {os.path.basename(item_path)}")
                    
                    # Create metadata labels
                    ttk.Label(metadata_window, text="Path:", font=('Arial', 10)).pack(pady=5)
                    ttk.Label(metadata_window, text=item_path, wraplength=400).pack()
                    
                    ttk.Label(metadata_window, text="\nDetails:", font=('Arial', 10, 'bold')).pack()
                    for key, value in metadata.items():
                        ttk.Label(metadata_window, text=f"{key}: {value}").pack()
                    
                    # Add close button
                    ttk.Button(metadata_window, text="Close", 
                            command=metadata_window.destroy).pack(pady=10)
                    
        except IndexError:
            messagebox.showinfo("Error", "Please select an item first")

    def get_metadata(self, path):
        """Retrieve metadata for file/folder"""
        metadata = {
            "Type": "File" if os.path.isfile(path) else "Folder",
            "Size": f"{os.path.getsize(path):,} bytes" if os.path.isfile(path) 
                    else "N/A (folder)",
            "Created": datetime.fromtimestamp(os.path.getctime(path)).strftime("%Y-%m-%d %H:%M:%S"),
            "Modified": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"),
            "Permissions": oct(stat.S_IMODE(os.stat(path).st_mode))
        }
        return metadata


    def deselect_on_empty_space(self, event):
        """Deselect all items when clicking on empty space"""
        # Get the item (row) that was clicked
        item = self.file_tree.identify_row(event.y)       
        # If not clicking on a row (empty space), clear selection
        if not item:
            self.file_tree.selection_set([])  # Alternative way to clear
            self.file_tree.focus("")  # Clear focus as well
            return "break"

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

                    log_action(self.username, 'RENAME', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} → {new_path}")

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

            log_action(self.username, 'CREATE', 'FILE', file_path)

            self.update_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not create file: {e}")

    def create_folder(self):
        foldername = simpledialog.askstring("Create Folder", "Enter folder name:")
        if 'Automation_Window' in foldername:
            messagebox.showerror("Error", "You cannot create folder with this name.")
            return
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

            log_action(self.username, 'CREATE', 'FOLDER', folder_path)

            self.update_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not create folder: {e}")

    def delete_item(self):
        selection = self.file_tree.selection()
        if not selection:
            return
        
        selection_count = len(selection)        
        # For single item selection, use existing logic
        if selection_count == 1:
            item_id = selection[0]
            item_values = self.file_tree.item(item_id, 'values')
            if not item_values:
                return
                
            item_type, item_path = item_values

            # Check if it's the other automation folder
            if 'Atomation_Window' in os.path.basename(item_path) and self.username not in os.path.basename(item_path):
                messagebox.showerror("Error", "You cannot delete this folder.")
                return
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
                        log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', item_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not delete automation folder: {e}")
                    finally:
                        conn.close()
                    self.update_file_list()
                    return
            
            # Regular deletion process for non-automation single item
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
                        log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', item_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not delete item: {e}")
                else:
                    shutil.move(item_path, self.bin_dir)
                    log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', item_path)
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
                        log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', item_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not delete item: {e}")
        else:
            # Multiple items selected
            # Check if we are in the bin directory
            if self.current_dir == self.bin_dir:
                confirm = messagebox.askokcancel("Permanent Deletion",
                    f"This will permanently delete {selection_count} items!\n\nAre you absolutely sure?",
                    icon=messagebox.WARNING)
                if not confirm:
                    return
                    
                # Track results
                success_count = 0
                failed_items = []
                
                for item_id in selection:
                    item_values = self.file_tree.item(item_id, 'values')
                    if item_values:
                        item_type, item_path = item_values
                        try:
                            if item_type == 'file':
                                os.remove(item_path)
                            elif item_type == 'folder':
                                shutil.rmtree(item_path, onexc=remove_readonly)
                            log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', item_path)
                            success_count += 1
                        except Exception as e:
                            failed_items.append(f"{os.path.basename(item_path)}: {str(e)}")
                
                # Show results
                if failed_items:
                    messagebox.showerror("Error", f"Deleted {success_count}/{selection_count} items.\n\nFailed items:\n" + "\n".join(failed_items))
                elif success_count > 0:
                    messagebox.showinfo("Success", f"Successfully deleted {success_count} items.")
            else:
                # Regular directory - ask whether to delete or move to bin
                response = messagebox.askyesnocancel("Multiple Items",
                    f"What would you like to do with these {selection_count} items?\n\nYes = Delete permanently\nNo = Move to Bin\nCancel = Abort operation")
                
                if response is None:  # Cancel
                    return                    
                # Track results
                success_count = 0
                failed_items = []
                skipped_items = []
                
                for item_id in selection:
                    item_values = self.file_tree.item(item_id, 'values')
                    if item_values:
                        item_type, item_path = item_values
                        
                        # Skip automation folder in batch operations
                        if self.automation_folder and os.path.normpath(item_path) == os.path.normpath(self.automation_folder):
                            skipped_items.append(f"{os.path.basename(item_path)} (automation folder)")
                            continue                        
                        try:
                            if response:  # Permanent delete

                                if item_type == 'file':
                                    os.remove(item_path)
                                elif item_type == 'folder':
                                    shutil.rmtree(item_path, onexc=remove_readonly)
                                log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', item_path)
                            else:  # Move to bin
                                shutil.move(item_path, self.bin_dir)
                                log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', item_path)
                            success_count += 1
                        except Exception as e:
                            failed_items.append(f"{os.path.basename(item_path)}: {str(e)}")
                
                # Show results
                if skipped_items:
                    messagebox.showinfo("Items Skipped", "The following items were skipped for safety:\n" + "\n".join(skipped_items))
                    
                if failed_items:
                    action = "deleted" if response else "moved to Bin"
                    messagebox.showerror("Error", f"{action.capitalize()} {success_count}/{selection_count} items.\n\nFailed items:\n" + "\n".join(failed_items))
                elif success_count > 0:
                    action = "deleted" if response else "moved to Bin"
                    messagebox.showinfo("Success", f"Successfully {action} {success_count} items.")
        
        self.update_file_list()


    def move_item(self):
        selection = self.file_tree.selection()
        if not selection:
            return
            
        # Show how many items are selected
        selection_count = len(selection)
        
        # Create custom dialog
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)  # Wait for dialog to close
        
        if dest_dialog.selected_path:
            dest = dest_dialog.selected_path
            dest_norm = os.path.normpath(dest)
            
            # Track success and failure
            success_count = 0
            failed_items = []
            skipped_items = []
            
            # Process each selected item
            for item_id in selection:
                item_values = self.file_tree.item(item_id, 'values')
                if item_values:
                    item_type, item_path = item_values
                    
                    # SAFETY CHECK: Prevent moving to the same parent folder
                    item_parent = os.path.dirname(os.path.normpath(item_path))
                    if item_parent == dest_norm:
                        skipped_items.append(f"{os.path.basename(item_path)} (already in destination)")
                        continue
                    
                    try:
                        base_name = os.path.basename(item_path)
                        dest_path = os.path.join(dest, base_name)
                        
                        # Handle file conflicts
                        if os.path.exists(dest_path):
                            if selection_count == 1:
                                # Single item - ask normally
                                confirm = messagebox.askyesno("Confirm Overwrite",
                                    f"'{base_name}' already exists in destination. Overwrite?")
                                if not confirm:
                                    continue
                            else:
                                # Multiple items - ask once with option to apply to all
                                if not hasattr(self, '_overwrite_all'):
                                    response = messagebox.askyesnocancel("Confirm Overwrite",
                                        f"'{base_name}' already exists in destination.\n\nYes = Overwrite this and all conflicts\nNo = Skip this item\nCancel = Abort operation")
                                    if response is None:  # Cancel
                                        break
                                    elif response:  # Yes
                                        self._overwrite_all = True
                                    else:  # No
                                        self._overwrite_all = False
                                        continue
                                elif not self._overwrite_all:
                                    continue
                            
                            # Remove existing destination
                            if item_type == 'file':
                                os.remove(dest_path)
                            elif item_type == 'folder':
                                shutil.rmtree(dest_path, onexc=remove_readonly)
                        
                        # Perform the move
                        shutil.move(item_path, dest)
                        log_action(self.username, 'MOVE', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} → {dest}")
                        success_count += 1
                        
                    except Exception as e:
                        failed_items.append(f"{base_name}: {str(e)}")
            
            # Clean up temporary attribute
            if hasattr(self, '_overwrite_all'):
                delattr(self, '_overwrite_all')
            
            # Show skipped items message
            if skipped_items:
                messagebox.showinfo("Items Skipped", 
                    "The following items were not moved because they are already in the destination folder:\n" + 
                    "\n".join(skipped_items))
            
            # Show results
            if failed_items:
                messagebox.showerror("Error", f"Moved {success_count}/{selection_count} items.\n\nFailed items:\n" + "\n".join(failed_items))
            elif success_count > 0:
                messagebox.showinfo("Success", f"Successfully moved {success_count} items to {os.path.basename(dest)}")
            
            self.update_file_list()

    def copy_item(self):
        selection = self.file_tree.selection()
        if not selection:
            return
            
        # Show how many items are selected
        selection_count = len(selection)
        
        # Create custom dialog
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)  # Wait for dialog to close
        
        if dest_dialog.selected_path:
            dest = dest_dialog.selected_path
            dest_norm = os.path.normpath(dest)
            
            # Check if any items are being copied to their parent folder
            same_parent_items = []
            for item_id in selection:
                item_values = self.file_tree.item(item_id, 'values')
                if item_values:
                    item_type, item_path = item_values
                    item_parent = os.path.dirname(os.path.normpath(item_path))
                    if item_parent == dest_norm:
                        same_parent_items.append(os.path.basename(item_path))
            
            # If copying to same parent folder, ask if they want to create duplicates
            if same_parent_items:
                if len(same_parent_items) == 1:
                    msg = f"'{same_parent_items[0]}' is already in this folder. Create a duplicate copy?"
                else:
                    msg = f"{len(same_parent_items)} items selected are already in this folder. Create duplicate copies?"
                    
                create_duplicates = messagebox.askyesno("Redundant Operation", msg)
                if not create_duplicates:
                    # Filter out items that are in the same parent folder
                    filtered_selection = []
                    for item_id in selection:
                        item_values = self.file_tree.item(item_id, 'values')
                        if item_values:
                            item_type, item_path = item_values
                            item_parent = os.path.dirname(os.path.normpath(item_path))
                            if item_parent != dest_norm:
                                filtered_selection.append(item_id)
                    
                    # Update selection
                    if not filtered_selection:
                        messagebox.showinfo("Operation Cancelled", "No items to copy.")
                        return
                    selection = filtered_selection
                    selection_count = len(selection)
            
            # Track success and failure
            success_count = 0
            failed_items = []
            
            # Process each selected item
            for item_id in selection:
                item_values = self.file_tree.item(item_id, 'values')
                if item_values:
                    item_type, item_path = item_values
                    
                    try:
                        base_name = os.path.basename(item_path)
                        dest_path = os.path.join(dest, base_name)
                        
                        # Handle file conflicts
                        if os.path.exists(dest_path):
                            if selection_count == 1:
                                # Single item - ask normally
                                confirm = messagebox.askyesno("Confirm Overwrite",
                                    f"'{base_name}' already exists in destination. Overwrite?")
                                if not confirm:
                                    continue
                            else:
                                # Multiple items - ask once with option to apply to all
                                if not hasattr(self, '_overwrite_all'):
                                    response = messagebox.askyesnocancel("Confirm Overwrite",
                                        f"'{base_name}' already exists in destination.\n\nYes = Overwrite this and all conflicts\nNo = Skip this item\nCancel = Abort operation")
                                    if response is None:  # Cancel
                                        break
                                    elif response:  # Yes
                                        self._overwrite_all = True
                                    else:  # No
                                        self._overwrite_all = False
                                        continue
                                elif not self._overwrite_all:
                                    continue
                            
                            # Remove existing destination
                            if item_type == 'file':
                                os.remove(dest_path)
                            elif item_type == 'folder':
                                shutil.rmtree(dest_path, onexc=remove_readonly)
                        
                        # Perform the copy

                        if item_type == 'file':
                            shutil.copy2(item_path, dest)
                        elif item_type == 'folder':
                            shutil.copytree(item_path, dest_path)
                        log_action(self.username, 'COPY', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} copy→ {dest}")
                        
                        success_count += 1
                        
                    except Exception as e:
                        failed_items.append(f"{base_name}: {str(e)}")
            
            # Clean up temporary attribute
            if hasattr(self, '_overwrite_all'):
                delattr(self, '_overwrite_all')
            
            # Show results
            if failed_items:
                messagebox.showerror("Error", f"Copied {success_count}/{selection_count} items.\n\nFailed items:\n" + "\n".join(failed_items))
            elif success_count > 0:
                messagebox.showinfo("Success", f"Successfully copied {success_count} items to {os.path.basename(dest)}") 
            self.update_file_list()



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
        self.current_dir = self.bin_dir
        self.update_file_list()


    def empty_bin(self):
        """Empty all items from the DocuVault bin permanently"""
        # Check if we're in the bin directory
        if self.current_dir != self.bin_dir:
            messagebox.showinfo("Info", "You need to be in the Bin to empty it.")
            return
            
        # Check if bin is empty
        try:
            items = os.listdir(self.bin_dir)
            if not items:
                messagebox.showinfo("Info", "The Bin is already empty.")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Could not access Bin: {e}")
            return
            
        # Confirm before permanently deleting
        confirm = messagebox.askokcancel(
            "Empty Bin",
            "This will permanently delete all items in the Bin!\n\nAre you absolutely sure?",
            icon=messagebox.WARNING
        )        
        if not confirm:
            return
            
        # Empty the bin
        try:
            for item in os.listdir(self.bin_dir):
                item_path = os.path.join(self.bin_dir, item)                
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        item_type = 'file'
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path, onexc=remove_readonly)
                        item_type = 'folder'
                    log_action(self.username, 'DELETE', 'FILE' if item_type=='file' else 'FOLDER', f"{item_path}", "Empty Bin")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete {item}: {e}")                    
            messagebox.showinfo("Success", "Bin has been emptied.")
            self.update_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to empty Bin: {e}")


    def restore_item(self):
        selection = self.file_tree.selection()
        if not selection:
            return
        
        selection_count = len(selection)
        
        # Create custom directory dialog
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)
        
        if dest_dialog.selected_path:
            dest = dest_dialog.selected_path
            dest_norm = os.path.normpath(dest)
            
            # Verify destination is different from bin
            if dest == self.bin_dir:
                messagebox.showwarning("Invalid Destination",
                    "Cannot restore items back to the Recycle Bin")
                return
            
            # Track success and failure
            success_count = 0
            failed_items = []
            
            # Process each selected item
            for item_id in selection:
                item_values = self.file_tree.item(item_id, 'values')
                if item_values:
                    item_type, item_path = item_values
                    
                    try:
                        base_name = os.path.basename(item_path)
                        dest_path = os.path.join(dest, base_name)
                        
                        # For batch operations, handle conflicts intelligently
                        if os.path.exists(dest_path):
                            if selection_count == 1:
                                # Single item - ask normally
                                confirm = messagebox.askyesno("Confirm Overwrite",
                                    f"'{base_name}' already exists in destination. Overwrite?")
                                if not confirm:
                                    continue
                            else:
                                # Multiple items - ask once with option to apply to all
                                if not hasattr(self, '_overwrite_all'):
                                    response = messagebox.askyesnocancel("Confirm Overwrite",
                                        f"'{base_name}' already exists in destination.\n\nYes = Overwrite this and all conflicts\nNo = Skip this item\nCancel = Abort operation")
                                    if response is None:  # Cancel
                                        break
                                    elif response:  # Yes
                                        self._overwrite_all = True
                                    else:  # No
                                        self._overwrite_all = False
                                        continue
                                elif not self._overwrite_all:
                                    continue
                            
                            # Remove existing destination
                            if os.path.isfile(dest_path):
                                os.remove(dest_path)
                            elif os.path.isdir(dest_path):
                                shutil.rmtree(dest_path, onexc=remove_readonly)
                        
                        # Perform restore operation
                        shutil.move(item_path, dest)
                        log_action(self.username, 'RESTORE', 'FILE' if item_type=='file' else 'FOLDER', f"{item_path} → {dest}")
                        success_count += 1
                        
                    except Exception as e:
                        failed_items.append(f"{base_name}: {str(e)}")
            
            # Clean up temporary attribute
            if hasattr(self, '_overwrite_all'):
                delattr(self, '_overwrite_all')
            
            # Show results
            if failed_items:
                messagebox.showerror("Error", f"Restored {success_count}/{selection_count} items.\n\nFailed items:\n" + "\n".join(failed_items))
            elif success_count > 0:
                messagebox.showinfo("Success", f"Successfully restored {success_count} items to {os.path.basename(dest)}")
            
            # Update file list and restore original directory
            self.update_file_list()
            self.current_dir = self.bin_dir  # Stay in bin after restore

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

        
    def show_activity_log(self):
        LogViewer(self.root, self.username)

    ##############################
    # Cloud Operations Callbacks #
    def get_master_password(self):
        """Prompt for master password when needed"""
        return simpledialog.askstring("Security Check", 
                                    "Enter your master password for auto-connecting to cloud:",
                                    show='*')
    
    def show_progress(self, message):
        """Create progress popup"""
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
        """Update progress bar and label"""
        if message:
            self.progress_label.config(text=message)
        self.progress_bar['value'] = value
        # Update cloud status based on progress messages
        if value >= 100 and message:
            if "Connected to Nextcloud" in message:
                self.update_cloud_status('connected')
            self.progress_window.after(2000, self.progress_window.destroy)

    def delete_cloud_item(self, cloud_path):
        remote_path = f"/DocuVault/{os.path.basename(cloud_path)}"
        if messagebox.askyesno("Confirm", "Delete from cloud?"):
            self.cloud.delete_file(remote_path)
    
    def show_error(self, message):
        """Show error message from cloud ops"""
        messagebox.showerror("Cloud Error", message)
        # Update cloud status if it's a connection error
        if "Connection failed" in message:
            self.update_cloud_status('failed')
        # Destroy progress window if it exists
        if hasattr(self, 'progress_window') and self.progress_window and tk.Toplevel.winfo_exists(self.progress_window):
            self.progress_window.destroy()

    def show_info(self, message):
        """Show info message from cloud ops"""
        messagebox.showinfo("Cloud Info", message)

    def show_cloud_config(self):
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
            tk.Label(config_win, text=label).pack()
            entry = tk.Entry(config_win)
            entry.pack()
            entry_widgets[field_name] = entry
        
        def save_config():
            self.cloud.store_credentials(
                server_url=entry_widgets["server_url"].get(),
                cloud_user=entry_widgets["cloud_user"].get(),
                cloud_pass=entry_widgets["cloud_pass"].get(),
                master_password=self.get_master_password()
            )
            config_win.destroy()
        
        tk.Button(config_win, text="Save", command=save_config).pack()

    def display_cloud_results(self, results):
        if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
            self.search_tree.tag_configure(tagname='cloud', foreground='blue')
            # Check if results are empty
            if not results or len(results) == 0:
                self.search_tree.insert("", "end",
                                    text="No matching cloud records",
                                    values=("",),
                                    tags=('cloud',))
                return  
            # Insert results with the cloud tag
            for item in results:
                self.search_tree.insert("", "end", 
                    text=item.name,
                    values=(f"Cloud: {item.user_path}",),
                    tags=('cloud',)
                )

    def search_cloud_files(self):
        """Search only in cloud storage"""
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
            
            # Check if connected to cloud
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
            # Check if file already exists
            if os.path.exists(local_path):
                # Ask if user wants to overwrite
                overwrite = messagebox.askyesno(
                    "File Already Exists", 
                    f"The file '{filename}' already exists in the destination folder.\n\nDo you want to overwrite it?"
                )                
                if not overwrite:
                    # Ask if user wants to rename
                    rename = messagebox.askyesno(
                        "Rename File", 
                        "Do you want to rename the downloading file?"
                    )                    
                    if rename:
                        # Get new name from user
                        new_name = simpledialog.askstring(
                            "Rename File", 
                            "Enter a new name for the file:"
                        )                        
                        if not new_name:
                            messagebox.showinfo("Info", "Download canceled")
                            return                        
                        # Make sure the new name has the correct extension
                        file_ext = os.path.splitext(filename)[1]
                        if not new_name.endswith(file_ext):
                            new_name += file_ext                        
                        # Check if the new name also exists
                        new_path = os.path.join(dest_dir, new_name)
                        if os.path.exists(new_path):
                            messagebox.showerror("Error", f"A file named '{new_name}' also exists. Download aborted.")
                            return                        
                        # Download with new name
                        self.cloud.download_file(
                            remote_path=remote_path,
                            local_dir=dest_dir,
                            custom_local_path=new_path
                        )
                        return
                    else:
                        # User doesn't want to rename or overwrite
                        messagebox.showinfo("Info", "Download canceled")
                        return
            
            # If we got here, either the file doesn't exist or the user wants to overwrite
            self.cloud.download_file(
                remote_path=remote_path,
                local_dir=dest_dir
            )

    def upload_to_cloud(self, local_path):
        if self.cloud and self.cloud.nc:
            self.cloud.upload_file(local_path, f"/DocuVault/{os.path.basename(local_path)}")
        else:
            messagebox.showinfo("Cloud Search", "Please connect to cloud first")

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

