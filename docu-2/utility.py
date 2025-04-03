
import tkinter as tk
from tkinter import ttk
import os
from tkinter import messagebox
import time
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text

def txt_from_pdf(pdf_path, output_path): 
    try:
        # Extract text using pdfminer.six
        text = extract_text(pdf_path)
        
        # Write the extracted text to the output file
        with open(output_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)
            
        return True
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return False

def compare_path(st, pt):
    l1 = st.split('\\')
    l1_ = st.split('/')
    l2 = pt.split('\\')
    l2_ = pt.split('/')
    return l1_ == l2 or l1 == l2_ or l1 == l2 or l1_ == l2_

class CustomDirectoryDialog(tk.Toplevel):
    def __init__(self, parent, current_dir):
        super().__init__(parent)

        # Bind events to track user activity
        self.bind("<Key>", lambda e: parent.user_activity())
        self.bind("<Motion>", lambda e: parent.user_activity())
        self.bind("<Button>", lambda e: parent.user_activity())

        self.title("Select Destination Folder")
        self.geometry("600x400")

        # Set application icon
        try:
            self.iconbitmap("AppIcon\\DocuVault-icon.ico")
        except Exception as e:
            pass
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

        btn_frame.pack(fill = tk.X, pady=5)
        
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Select", command=self.on_select).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="↩ Back", command=self.go_back).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🏠 Home", command=lambda: self.navigate_to_special(os.path.expanduser("~"))).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="💻 Desktop", command=lambda: self.navigate_to_special(os.path.join(os.path.expanduser("~"), "OneDrive\\Desktop"))).pack(side=tk.LEFT, padx=5)
        
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

        if self.current_dir != os.path.expanduser("~"):
            parent_dir = os.path.dirname(self.current_dir)
            if os.path.exists(parent_dir):
                self.current_dir = parent_dir
                self.path_label.config(text=self.current_dir)
                self.populate_tree(self.current_dir)
        else:
            messagebox.showinfo("Home Directory", "You are already at the home directory.")

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


class CustomFileDialog(tk.Toplevel):
    def __init__(self, parent, initial_dir):
        super().__init__(parent)
        self.title("Select File")
        self.geometry("600x400")

        # Set application icon
        self.selected_file = None
        self.temp_selection = None
        self.current_dir = initial_dir
        self.grab_set()
        self.file_types = ['.txt','.jpg','.jpeg','.png','.pdf']  # Add/remove as needed

        # UI Components
        self.path_label = tk.Label(self, text=self.current_dir)
        self.path_label.pack(pady=5)

        # Configure Treeview
        self.file_tree = ttk.Treeview(self)
        self.file_tree.pack(expand=True, fill=tk.BOTH)
        
        # Configure columns properly
        self.file_tree["columns"] = ("type", "fullpath")
        self.file_tree.column("#0", width=400, anchor=tk.W)
        self.file_tree.column("type", width=150, anchor=tk.W)
        self.file_tree.column("fullpath", width=0, stretch=tk.NO)
        
        self.file_tree.heading("#0", text="Name", anchor=tk.W)
        self.file_tree.heading("type", text="Type", anchor=tk.W)

        # Add tag configurations
        self.file_tree.tag_configure('file', foreground='blue')
        self.file_tree.tag_configure('folder', foreground='green')
        self.file_tree.tag_configure('parent', foreground='gray')

        # Navigation controls
        nav_frame = tk.Frame(self)
        nav_frame.pack(pady=5)
        ttk.Button(nav_frame, text="Select", command=self.on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="↩ Back", command=self.go_back).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="🏠 Home", 
                 command=lambda: self.navigate_to_special(os.path.expanduser("~"))).pack(side=tk.LEFT, padx=5)

        # Event bindings
        self.file_tree.bind("<<TreeviewSelect>>", self.on_single_click)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        
        # Initial population
        self.populate_tree(self.file_tree, self.current_dir)

    def populate_tree(self, tree, directory, parent="", depth=0):
        """Fixed tree population with proper error handling"""
        try:
            # Clear existing items first
            for item in tree.get_children(parent):
                tree.delete(item)

            # Add parent directory entry
            if depth > 0:
                parent_dir = os.path.dirname(directory)
                tree.insert(parent, 'end', text="..", 
                          values=('parent', parent_dir),
                          tags=('parent',), 
                          open=False)

            # Get directory contents with error handling
            try:
                items = os.listdir(directory)
            except PermissionError:
                if depth == 0:
                    messagebox.showwarning("Access Denied", 
                        f"Permission denied for:\n{directory}")
                return
            except Exception as e:
                messagebox.showerror("Error", 
                    f"Directory access error: {str(e)}")
                return

            # Process items with visual feedback
            for idx, item in enumerate(sorted(items)):
                item_path = os.path.join(directory, item)
                
                # Skip system directories (Windows only)
                if os.name == 'nt' and any(sub in item_path.lower() 
                    for sub in ('windows', 'program files', 'programdata')):
                    continue

                try:
                    if os.path.isfile(item_path):
                        ext = os.path.splitext(item)[1].lower()
                        if ext in self.file_types:
                            tree.insert(parent, 'end', text=item, 
                                      values=('file', item_path),
                                      tags=('file',))
                        
                    elif os.path.isdir(item_path):
                        node = tree.insert(parent, 'end', text=item, 
                                        values=('folder', item_path),
                                        tags=('folder',),
                                        open=False)
                        # Limited recursion for performance
                        if depth < 2:
                            self.populate_tree(tree, item_path, node, depth+1)
                            
                    # Update UI periodically
                    if idx % 20 == 0:
                        tree.update_idletasks()
                        
                except PermissionError:
                    continue  # Skip items without access
                except Exception as e:
                    messagebox.showerror("Error", 
                        f"Couldn't process {item}:\n{str(e)}")

        except Exception as e:
            messagebox.showerror("Critical Error", 
                f"Tree population failed:\n{str(e)}")

    def on_single_click(self, event):
        """Handle file selection"""
        try:
            item = self.file_tree.selection()[0]
            values = self.file_tree.item(item, "values")
            if values and len(values) >= 2:
                # Store selection only if it's a file
                self.temp_selection = values[1] if values[0] == 'file' else None
        except IndexError:
            self.temp_selection = None

    def on_double_click(self, event):
        """Handle directory navigation or file selection"""
        try:
            item = self.file_tree.selection()[0]
            values = self.file_tree.item(item, "values")
            
            if values:
                item_type, full_path = values
                if item_type == 'folder':
                    self.current_dir = full_path
                    self.path_label.config(text=self.current_dir)
                    self.populate_tree(self.file_tree, self.current_dir)
                elif item_type == 'file':
                    self.selected_file = full_path
                    self.destroy()
        except IndexError:
            pass

    def on_select(self):
        """Final selection handler"""
        if self.temp_selection and os.path.isfile(self.temp_selection):
            self.selected_file = self.temp_selection
            self.destroy()
        else:
            messagebox.showwarning("Invalid Selection", "Please select a file")

    def go_back(self):
        """Navigate up one directory"""
        parent = os.path.dirname(self.current_dir)
        if os.path.exists(parent):
            self.current_dir = parent
            self.path_label.config(text=self.current_dir)
            self.populate_tree(self.file_tree, self.current_dir)

    def navigate_to_special(self, path):
        """Navigate to special directories"""
        if os.path.exists(path):
            self.current_dir = path
            self.path_label.config(text=self.current_dir)
            self.populate_tree(self.file_tree, self.current_dir)

    def update_file_list(self):
        """Refresh the tree view"""
        self.populate_tree(self.file_tree, self.current_dir)




