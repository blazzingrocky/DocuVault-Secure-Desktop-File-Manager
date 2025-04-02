import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import sqlite3
import subprocess
from tkinter import ttk  # For the Treeview widget
from utility import CustomDirectoryDialog, CustomFileDialog, compare_path
import requests
from database import log_action
#from encryption import FileEncryptor
import time
import threading
import win32api
import win32con
import os
import stat

class AutomationWindow(tk.Toplevel):
    def __init__(self, parent, automation_folder, username):
        super().__init__(parent)
        self.parent = parent
        self.title("Automation Window")
        self.geometry("800x600")
        self.automation_folder = automation_folder
        self.username = username
        self.encryptor = FileEncryptor(username=self.username)
        self.encryption_enabled = tk.BooleanVar(value=True)

        # Set theme like gui2.py
        self._set_theme()
        self._create_widgets()
        self._setup_layout()

        if self.automation_folder is None or not os.path.exists(self.automation_folder):
            self._show_initial_setup()
        else:
            self.current_dir = self.automation_folder
            self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')
            self.create_auto_folders()
            self.update_file_list()
    # In automation.py - modify the set_automation_folder method

    def _set_theme(self):
        try:
            self.tk.call("source", "azure.tcl")
            self.tk.call("set_theme", "dark")
        except tk.TclError:
            self.style = ttk.Style()
            self.style.theme_use('clam')

    def create_auto_folders(self):
        self.folders = ["txt", "image"]
        for folder in self.folders:
            os.makedirs(os.path.join(self.automation_folder, folder), exist_ok=True)
        self.subfolders = {
            "txt": ["legal", "literary", "technical"],
            "image": []
        }
        for folder, subfolders in self.subfolders.items():
            for subfolder in subfolders:
                os.makedirs(os.path.join(self.automation_folder, folder, subfolder), exist_ok=True)
   
    def set_automation_folder(self):
        confirm = messagebox.askyesno("Automation Setup", "Do you want to set up automation?")
        if confirm:
            self.automation_folder = os.path.join(os.path.expanduser("~"), f"Automation_Window_{self.username}")
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


    def _create_widgets(self):
        # Top Navigation Frame
        self.top_frame = ttk.Frame(self)
        self.path_label = ttk.Label(self.top_frame, font=('TkDefaultFont', 10, 'bold'))
        
        # Main File Tree
        self.file_tree = ttk.Treeview(self, columns=('type', 'path'), show='tree headings')
        self.file_tree.heading('#0', text='Name')
        self.file_tree.heading('type', text='Type')
        self.file_tree.heading('path', text='Path')
        self.file_tree.column('#0', width=250)
        self.file_tree.column('type', width=100)
        self.file_tree.column('path', width=400)

        # Toolbar Frame
        self.toolbar = ttk.Frame(self)
        self.buttons = [
            ('🗋 Create File', self.create_file),
            ('📁 Create Folder', self.create_folder),
            ('✂️ Cut', lambda: self.move_item),
            ('📋 Copy', lambda: self.copy_item),
            ('🗑 Delete', self.delete_item),
            ('🔄 Refresh', self.update_file_list)
        ]

        # Encryption Panel
        self.encryption_frame = ttk.LabelFrame(self, text="File Encryption")
        self.encryption_check = ttk.Checkbutton(
            self.encryption_frame, 
            text="Enable Encryption", 
            variable=self.encryption_enabled
        )
        self.encrypt_btn = ttk.Button(self.encryption_frame, text="Encrypt All", command=self.encrypt_all_files)
        self.decrypt_btn = ttk.Button(self.encryption_frame, text="Decrypt All", command=self.decrypt_all_files)
        self.pwd_btn = ttk.Button(self.encryption_frame, text="Set Password", command=self.set_encryption_password)

    def _setup_layout(self):
        # Top Frame
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)
        self.path_label.pack(side=tk.LEFT)
        
        # Toolbar Buttons
        self.toolbar.pack(fill=tk.X, padx=5, pady=2)
        for text, cmd in self.buttons:
            btn = ttk.Button(self.toolbar, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=2)

        # File Tree
        tree_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.file_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.configure(yscrollcommand=tree_scroll.set)
        self.file_tree.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Encryption Panel
        self.encryption_frame.pack(fill=tk.X, padx=5, pady=5)
        self.encryption_check.pack(side=tk.LEFT, padx=5)
        self.pwd_btn.pack(side=tk.LEFT, padx=5)
        self.encrypt_btn.pack(side=tk.LEFT, padx=5)
        self.decrypt_btn.pack(side=tk.LEFT, padx=5)

        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Open", command=self.open_file)
        self.context_menu.add_command(label="Rename", command=self.rename_item)
        self.context_menu.add_command(label="Delete", command=self.delete_item)
        self.context_menu.add_command(label="Properties", command=self.show_properties)

    def _show_initial_setup(self):
        ttk.Label(self, text="Automation Setup Required", font=('TkDefaultFont', 14)).pack(pady=20)
        ttk.Button(self, 
            text="Configure Automation Folder", 
            command=self.set_automation_folder,
            style='Accent.TButton'
        ).pack(pady=10)

    # Keep all original functionality methods unchanged below...
    # (create_auto_folders, set_automation_folder, upload_to_auto, etc.)
    # Only modify the GUI-related methods

    def update_file_list(self):
        # Update with ttk styling
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        # Add items with icons
        if self.current_dir != self.automation_folder:
            self.file_tree.insert('', 'end', text='..', values=('Parent Folder', self.current_dir),
                                 tags=('parent',), image='')
        
        for item in os.listdir(self.current_dir):
            item_path = os.path.join(self.current_dir, item)
            is_dir = os.path.isdir(item_path)
            self.file_tree.insert('', 'end', text=item,
                                  values=('Folder' if is_dir else 'File', item_path),
                                  tags=('dir' if is_dir else 'file'))

    def show_context_menu(self, event):
        # Update context menu styling
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # Add these new methods to the AutomationWindow class
    def set_encryption_password(self):
        """Set or change the master encryption password"""
        password = simpledialog.askstring("Encryption", 
                                        "Enter master encryption password:", 
                                        show='*')
        if password:
            # Initialize encryptor with new password
            self.encryptor = FileEncryptor(username=self.username, 
                                        master_password=password)
            
            # Generate and save a new master key
            try:
                key = self.encryptor.get_master_key()
                messagebox.showinfo("Encryption", 
                                    "Master password set successfully")
            except Exception as e:
                messagebox.showerror("Encryption Error", str(e))

    def encrypt_all_files(self):
        """Encrypt all files in the automation folder"""
        if not messagebox.askyesno("Confirm", 
                                "Encrypt all files in the automation folder?"):
            return
        
        try:
            encrypted_files = self.encryptor.encrypt_folder(self.automation_folder)
            messagebox.showinfo("Encryption", 
                            f"Successfully encrypted {len(encrypted_files)} files")
            self.update_file_list()
        except Exception as e:
            messagebox.showerror("Encryption Error", str(e))

    def decrypt_all_files(self):
        """Decrypt all files in the automation folder"""
        if not messagebox.askyesno("Confirm", 
                                "Decrypt all files in the automation folder?"):
            return
        
        try:
            decrypted_files = self.encryptor.decrypt_folder(self.automation_folder)
            messagebox.showinfo("Decryption", 
                            f"Successfully decrypted {len(decrypted_files)} files")
            self.update_file_list()
        except Exception as e:
            messagebox.showerror("Decryption Error", str(e))

    def upload_to_auto(self):
        file_dialog = CustomFileDialog(self.parent, self.current_dir)
        self.parent.wait_window(file_dialog)
        selected_path = file_dialog.selected_file
       
        if not selected_path:
            return
       
        if not os.path.isfile(selected_path):
            messagebox.showerror("Error", "Please select a file, not a directory")
            return


        # Create necessary directory structure
        self.classify_and_upload(selected_path)
        if self.encryption_enabled.get():
            try:
                encrypted_path = self.encryptor.encrypt_file(selected_path)
                # Set the encrypted file to read-only
                self.encryptor.set_file_permissions(encrypted_path, read_only=True)
            except Exception as e:
                messagebox.showwarning("Encryption Warning",
                                       f"File copied but not encrypted: {str(e)}")
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
    def classify_and_upload(self, selected_path):


        if self.automation_folder in selected_path:
            messagebox.showinfo("Info", "File is already in the automation folder.")
            return
        try:
            file_name = os.path.basename(selected_path)
            file_ext = os.path.splitext(file_name)[1].lower()


            dest_dir = self.automation_folder
            category_name = []
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
                    requests.get('http://10.145.115.74:8000/docs', timeout=2)
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
                        'http://10.145.115.74:8000/predict_txt',
                        files=files,
                        timeout=5
                    )
                    response.raise_for_status()
                    category_idx = response.json()['category']
                    category_name = [category_map.get(category_idx, 'unknown')]
                    # dest_dir = os.path.join(dest_dir, category_name)


            # Image file processing
            elif file_ext in ('.jpg', '.jpeg', '.png'):
                dest_dir = os.path.join(dest_dir, 'image')


                try:
                    requests.get('http://10.145.115.74:8002/docs', timeout=2)
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
                        'http://10.145.115.74:8002/predict_img',
                        files=files,
                        timeout=5
                    )
                    response.raise_for_status()
                    category_list = response.json()['Top 5 predicted classes']
                    # category_name = category_map.get(category_idx, 'unknown')
                    if category_list[0][0] > 0.6:
                        category_name = [category_list[0][1]]
                    elif category_list[0][0] > 0.3 and category_list[1][0] > 0.2:
                        category_name = [category_list[0][1], category_list[1][1]]
                    else:
                        category_name = ['unknown']
                    # dest_dir = os.path.join(dest_dir, category_name)
           
            else:
                messagebox.showerror(
                    "Unsupported Format",
                    f"Cannot process {file_ext} files\n"
                    "Supported formats: .txt, .jpg, .png"
                )
                return
           
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
    # Ensure destination directory exists
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
                
                # Encrypt the file if encryption is enabled
                if self.encryption_enabled.get():
                    try:
                        encrypted_path = self.encryptor.encrypt_file(dest_path)
                        # If encrypted successfully and path changed, update dest_path
                        if encrypted_path != dest_path:
                            dest_path = encrypted_path
                            final_name = os.path.basename(encrypted_path)
                    except Exception as e:
                        messagebox.showwarning("Encryption Warning", 
                                        f"File copied but not encrypted: {str(e)}")
                
                self.update_file_list()
            except Exception as e:
                messagebox.showerror("Error", f"Could not upload item: {e}")
                return
            
            log_action(self.username, 'AUTO_UPLOAD', 'FILE', f"{selected_path} → {dest_path}", f"classified as {category}")
            
            # Prepare success message
            success_msg = (f"Moved to: {os.path.relpath(dest_path, self.automation_folder)}\n"
                        f"Location: {dest_path}")
            success_msg = (f"Classified as {category}\n" + success_msg)
            success.append(success_msg)
        
        # Refresh if in automation directory
        if compare_path(self.current_dir, self.automation_folder):
            self.update_file_list()
        
        messagebox.showinfo("Success", "\n".join(success))
    # def upload(self, dest_dir, file_name, file_ext, selected_path, category_name):
    #     # Ensure destination directory exists
    #     if not category_name:
    #         return
    #     success = []
    #     temp = dest_dir
    #     for category in category_name:
    #         dest_dir = temp
    #         dest_dir = os.path.join(dest_dir, category)
    #         os.makedirs(dest_dir, exist_ok=True)
           
    #         # Generate unique filename
    #         base_name = os.path.splitext(file_name)[0]
    #         final_name = file_name
    #         counter = 1
           
    #         while os.path.exists(os.path.join(dest_dir, final_name)):
    #             final_name = f"{base_name}_{counter}{file_ext}"
    #             counter += 1
           
    #         dest_path = os.path.join(dest_dir, final_name)
           
    #         # Perform the file move
    #         try:
    #             shutil.copy2(selected_path, dest_path) # Copy instead of move
    #             self.update_file_list()
    #         except Exception as e:
    #             messagebox.showerror("Error", f"Could not upload item: {e}")
    #             return


    #         log_action(self.username, 'AUTO_UPLOAD', 'FILE', f"{selected_path} → {dest_path}", f"classified as {category}")
           
    #         # Prepare success message
    #         success_msg = (f"Moved to: {os.path.relpath(dest_path, self.automation_folder)}\n"
    #                     f"Location: {dest_path}")


    #         success_msg = (f"Classified as {category_name}\n" + success_msg)
    #         success.append(success_msg)


    #         # messagebox.showinfo("Success", success_msg)
           
    #         # Refresh if in automation directory
    #         if compare_path(self.current_dir, self.automation_folder):
    #             self.update_file_list()
    #     messagebox.showinfo("Success", "\n".join(success))

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
    # Check if file is encrypted
        if self.encryptor.is_file_encrypted(item_path):
            try:
                # Create temp directory if it doesn't exist
                temp_dir = os.path.join(self.automation_folder, '.temp')
                os.makedirs(temp_dir, exist_ok=True)
                
                # Decrypt file to temp location
                decrypted_path = self.encryptor.decrypt_for_viewing(item_path,temp_dir)
                self.encryptor.set_file_permissions(decrypted_path, read_only=True)
                # Open the decrypted file
                self._open_file_with_default_app(decrypted_path)
                
                # Schedule cleanup of temp files after some time (5 minutes)
                self.after(300000, lambda: self.encryptor.cleanup_temp_files(temp_dir))
                
            except Exception as e:
                messagebox.showerror("Decryption Error", str(e))
        else:
            # Open the file directly
            self._open_file_with_default_app(item_path)

# Add a helper method for opening files
    def _open_file_with_default_app(self, file_path):
        text_extensions = ['.txt', '.py', '.html', '.css', '.js', '.md']
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension in text_extensions:
            try:
                if os.name == 'nt':
                    subprocess.Popen(['notepad.exe', file_path])
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', file_path])
            except FileNotFoundError:
                messagebox.showerror("Error", "Text editor not found.")
        else:
            try:
                if os.name == 'nt':
                    os.startfile(file_path)
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', file_path])
            except OSError:
                messagebox.showerror("Error", "Cannot open this file type.")

    def modify_file(self, item_path):
        if self.encryptor.is_file_encrypted(item_path):
            try:
                # Create temp directory if it doesn't exist
                temp_dir = os.path.join(self.automation_folder, '.temp')
                os.makedirs(temp_dir, exist_ok=True)
                # Set the file to read-write
                # self.encryptor.set_file_permissions(item_path, read_only=False)
                 #Get the original filename
                filename = os.path.basename(item_path)
                if filename.endswith(self.encryptor.ENCRYPTION_EXTENSION):
                    filename = filename[:-len(self.encryptor.ENCRYPTION_EXTENSION)]
                    
                # Create a temporary file path
                temp_path = os.path.join(temp_dir, filename)
                # Decrypt the file to the temporary location
                decrypted_path = self.encryptor.decrypt_file(item_path,temp_path)
                # Make the decrypted file writable
                # decrypted_path=self.encryptor.decrypt_file(item_path)
                self.encryptor.set_file_permissions(decrypted_path, read_only=False)
                # Open the file for editing
                self._open_file_with_default_app(decrypted_path)
                # Start monitoring the file for changes
                self.encryptor.monitor_file_for_changes(decrypted_path)
                # Set the original encrypted file back to read-only
                try:
                    # Re-encrypt the file
                    if os.path.exists(decrypted_path):
                    # Make the original encrypted file writable
                        self.encryptor.set_file_permissions(item_path, read_only=False)
                        shutil.copyfile(decrypted_path, item_path)
                    # Re-encrypt the modified file
                        # temp=item_path
                        os.remove(decrypted_path)
                        # item_path=self.encryptor.encrypt_file(decrypted_path)
                    
                    # Set the re-encrypted file to read-only
                        self.encryptor.set_file_permissions(item_path, read_only=True)
                except Exception as e:
                    messagebox.showerror("Re-Encryption Error", str(e))
                # self.encryptor.set_file_permissions(item_path, read_only=True)

                # Schedule re-encryption after editing (e.g., 5 minutes)
                # self.after(300000, lambda: self._re_encrypt_file(decrypted_path, item_path))
            except Exception as e:
                    messagebox.showerror("Modification Error", str(e))
        else:
            # Open the file directly for editing
            self._open_file_with_default_app(item_path)
    def _re_encrypt_file(self, decrypted_path, original_path):
        try:
            # Re-encrypt the file
            encrypted_path = self.encryptor.encrypt_file(decrypted_path, original_path)
            
            # Set the encrypted file to read-only
            self.encryptor.set_file_permissions(encrypted_path, read_only=True)
            
            # Remove the decrypted file
            os.remove(decrypted_path)
            
            self.update_file_list()
        except Exception as e:
            messagebox.showerror("Re-encryption Error", str(e))
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
                context_menu.add_command(label="Modify", command=lambda: self.modify_file(item_path))
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