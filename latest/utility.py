# Add to imports at the top
import tkinter as tk
from tkinter import ttk
import os
from tkinter import messagebox
import time

def compare_path(st, pt):
    l1 = st.split('\\')
    l1_ = st.split('/')
    l2 = pt.split('\\')
    l2_ = pt.split('/')
    return l1_ == l2 or l1 == l2_ or l1 == l2 or l1_ == l2_

class CustomDirectoryDialog(tk.Toplevel):
    def __init__(self, parent, current_dir):
        super().__init__(parent)
        self.title("Select Destination Folder")
        self.geometry("600x400")
        self.selected_path = None
        self.temp_selection = None
        self.current_dir = current_dir
        self.grab_set()
        
        # Create widgets
        self.path_label = tk.Label(self, text=self.current_dir)
        self.path_label.pack(pady=5)
        
        self.tree = ttk.Treeview(self)
        self.tree.pack(expand=True, fill=tk.BOTH)
        
        # Configure columns
        self.tree["columns"] = ("type", "fullpath")
        self.tree.column("#0", width=300, minwidth=200)
        self.tree.column("type", width=100, minwidth=50)
        self.tree.column("fullpath", width=0, stretch=tk.NO)  # Hidden column
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        
        # Navigation buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="Select", command=self.on_select).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="↩ Back", command=self.go_back).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🏠 Home", command=lambda: self.navigate_to_special(os.path.expanduser("~"))).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📁 Desktop", command=lambda: self.navigate_to_special(os.path.join(os.path.expanduser("~"), "OneDrive\\Desktop"))).pack(side=tk.LEFT, padx=5)
        
        # Initial population with depth control
        # Single-click selection binding
        self.tree.bind("<<TreeviewSelect>>", self.on_single_click)
        self.populate_tree(self.current_dir, depth=0)
        self.tree.bind("<Double-1>", self.on_double_click)

    def populate_tree(self, directory, parent="", depth=0):
        """Safe directory population with proper path handling"""
        # Clear existing items
        for item in self.tree.get_children(parent):
            self.tree.delete(item)
        
        try:
            # Add parent directory entry with full path
            if depth > 0:
                parent_dir = os.path.dirname(directory)
                self.tree.insert(parent, "end", text="..", 
                               values=("parent", parent_dir), 
                               tags=("parent",), open=False)

            # Get directory contents with error handling
            try:
                items = os.listdir(directory)
            except PermissionError:
                if depth == 0:
                    messagebox.showwarning("Access Denied", 
                        f"Permission denied for directory:\n{directory}")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Could not access directory: {e}")
                return

            # Process items with full path tracking
            for idx, item in enumerate(items):
                item_path = os.path.join(directory, item)
                try:
                    if os.path.isdir(item_path):
                        # Store full path in hidden column
                        tree_id = self.tree.insert(parent, "end", text=item, 
                                                 values=("directory", item_path),
                                                 tags=("directory",), open=False)
                        # Limit recursion depth
                        if depth < 3:
                            self.populate_tree(item_path, tree_id, depth+1)
                            
                except PermissionError:
                    continue
                except Exception as e:
                    messagebox.showerror("Error", f"Could not process {item}")

        except Exception as e:
            messagebox.showerror("Critical Error", 
                f"Failed to populate directory structure: {str(e)}")

    def on_double_click(self, event):
        """Handle double-click with proper path retrieval"""
        try:
            item_id = self.tree.selection()[0]
        except IndexError: 
            return
        item_values = self.tree.item(item_id, "values")
        
        if item_values:
            item_type, full_path = item_values
            if item_type == "directory":
                self.current_dir = full_path
                self.path_label.config(text=self.current_dir)
                self.populate_tree(self.current_dir)
            elif item_type == "parent":
                self.current_dir = full_path
                self.path_label.config(text=self.current_dir)
                self.populate_tree(self.current_dir)

    def on_single_click(self, event):
        """Handle single-click selection with error prevention"""
        try:
            # Check if any item is selected
            selection = self.tree.selection()
            if not selection:
                return
                
            item_id = selection[0]
            
            # Verify item exists and has values
            if not self.tree.exists(item_id):
                return
                
            item_values = self.tree.item(item_id, 'values')
            if item_values and len(item_values) >= 2:
                self.temp_selection = item_values[1]  # Store full path
        except IndexError:
            # Handle empty selection during rapid clicks
            pass
        except Exception as e:
            messagebox.showerror("Selection Error", 
                f"Could not process selection: {str(e)}")


    def go_back(self):
        """Fixed back navigation"""
        parent_dir = os.path.dirname(self.current_dir)
        if os.path.exists(parent_dir):
            self.current_dir = parent_dir
            self.path_label.config(text=self.current_dir)
            self.populate_tree(self.current_dir)

    def on_select(self):
        """Handle selection with single-click preference"""
        if self.temp_selection and os.path.isdir(self.temp_selection):
            self.selected_path = self.temp_selection
        else:
            self.selected_path = self.current_dir
        self.destroy()

    def navigate_to_special(self, path):
        """Handle navigation to special directories"""
        if os.path.exists(path):
            self.current_dir = path
            self.path_label.config(text=self.current_dir)
            self.populate_tree(self.current_dir)
        else:
            messagebox.showwarning("Not Found", 
                f"Directory not found:\n{path}")
    # def is_there_file(self, path):
    #     return os.path.isfile(path)
