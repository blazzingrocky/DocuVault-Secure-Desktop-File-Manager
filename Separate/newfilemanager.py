import os
import stat
import shutil
import time
import sqlite3
import subprocess
from database import log_action
from tkinter import messagebox

def remove_readonly(func, path, _):
    """Remove read-only attribute from file before operations"""
    os.chmod(path, stat.S_IWRITE)  # Remove read-only flag
    func(path)

class FileManager:
    def __init__(self, username, bin_dir):
        self.username = username
        self.bin_dir = bin_dir
        self.automation_folder = self.get_automation_folder(username)
    
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
    
    def recursive_search(self, start_dir, search_term, parent=""):
        """Search recursively for files/folders matching search term"""
        results = []
        found = False
        
        try:
            items = os.listdir(start_dir)
        except PermissionError:
            return results, found
        except Exception as e:
            return results, found
        
        for item in items:
            item_path = os.path.join(start_dir, item)
            try:
                if search_term.lower() in item.lower():
                    results.append((item, item_path))
                    found = True
                
                if os.path.isdir(item_path):
                    sub_results, sub_found = self.recursive_search(item_path, search_term, parent)
                    results.extend(sub_results)
                    found = found or sub_found
            except PermissionError:
                continue
            except Exception:
                continue
        
        return results, found
    
    def rename_item(self, item_path, new_name):
        """Rename a file or folder"""
        try:
            item_type = 'file' if os.path.isfile(item_path) else 'folder'
            new_path = os.path.join(os.path.dirname(item_path), new_name)
            
            # Check if destination already exists
            if os.path.exists(new_path):
                confirm = messagebox.askyesno("Confirm Overwrite", 
                    f"'{new_name}' already exists. Overwrite?")
                if confirm:
                    if item_type == 'file':
                        os.remove(new_path)
                    elif item_type == 'folder':
                        shutil.rmtree(new_path, onexc=remove_readonly)
                else:
                    return True, item_path
    
            os.rename(item_path, new_path)
            log_action(self.username, 'RENAME', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} → {new_path}")
            return True, new_path
        except Exception as e:
            return False, f"Could not rename item: {e}"
    
    def get_available_apps(self, file_path):
        """Get list of available applications to open a file"""
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
                    ['grep', '-l', mime_type, '/usr/share/applications/*.desktop'],
                    universal_newlines=True
                ).split('\n')
                
                for app in apps:
                    if app:
                        app_name = os.path.basename(app).replace('.desktop', '')
                        available_apps.append((app_name, app))
            except Exception:
                # Fallback common Linux apps
                common_apps = [
                    ("gedit", "gedit"),
                    ("LibreOffice", "libreoffice"),
                    ("GIMP", "gimp")
                ]
                available_apps.extend(common_apps)
        
        return available_apps
    
    def open_file(self, item_path):
        """Open a file or directory with default application"""
        try:
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
                        return False, "Text editor not found."
                else:
                    try:
                        if os.name == 'nt':
                            os.startfile(item_path)
                        elif os.name == 'posix':
                            subprocess.Popen(['xdg-open', item_path])
                    except OSError:
                        return False, "Cannot open this file type."
                return True, "File opened successfully"
            elif os.path.isdir(item_path):
                return True, item_path  # Signal to navigate to this directory
            return False, "Path does not exist"
        except Exception as e:
            return False, f"Error opening file: {e}"
    
    def create_file(self, current_dir, filename):
        """Create a new file in the current directory"""
        if not filename:
            return False, "No filename provided"
        
        file_split = filename.split('.')
        count = 0
        for i in file_split:
            if len(i) > 0:
                count += 1
        
        if (count == 0 or len(file_split[-1]) <= 0):
            return False, "Please enter a valid file name."
        
        file_path = os.path.join(current_dir, filename)
        
        # Check if destination already exists
        if os.path.exists(file_path):
            confirm = messagebox.askyesno("Confirm Overwrite", 
                f"'{filename}' already exists. Overwrite?")
            if not confirm:
                return
        
        try:
            with open(file_path, 'w') as f:
                pass
            log_action(self.username, 'CREATE', 'FILE', file_path)
            return True, file_path
        except Exception as e:
            return False, f"Could not create file: {e}"
    
    def create_folder(self, current_dir, foldername):
        """Create a new folder in the current directory"""
        if not foldername:
            return False, "No folder name provided"
        
        folder_split = foldername.split('.')
        count = 0
        for i in folder_split:
            if len(i) > 0:
                count += 1
        
        if count == 0:
            return False, "Please enter a valid folder name."
        
        folder_path = os.path.join(current_dir, foldername)
        
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
            return True, folder_path
        except Exception as e:
            return False, f"Could not create folder: {e}"
    
    def delete_item(self, current_dir, items, permanently=False):
        """Delete files/folders (move to bin or permanently delete)"""
        # Track results
        success_count = 0
        failed_items = []
        skipped_items = []
        
        for item_path in items:
            # Skip if path doesn't exist
            if not os.path.exists(item_path):
                continue
                
            item_type = 'file' if os.path.isfile(item_path) else 'folder'
            
            # Check if it's the automation folder
            if self.automation_folder and os.path.normpath(item_path) == os.path.normpath(self.automation_folder):
                skipped_items.append(f"{os.path.basename(item_path)} (automation folder)")
                continue
            
            try:
                if permanently or current_dir == self.bin_dir:
                    # Permanent deletion
                    if item_type == 'file':
                        os.remove(item_path)
                    elif item_type == 'folder':
                        shutil.rmtree(item_path, onexc=remove_readonly)
                    log_action(self.username, 'DELETE', item_type.upper(), item_path)
                else:
                    # Move to bin
                    base_name = os.path.basename(item_path)
                    dest_path = os.path.join(self.bin_dir, base_name)
    
                # Handle name conflicts by appending a counter
                    counter = 1
                    while os.path.exists(dest_path):
                    # Get file name and extension
                        file_name, file_ext = os.path.splitext(base_name)
                    # Create a new name with counter
                        new_name = f"{file_name}_{counter}{file_ext}"
                        dest_path = os.path.join(self.bin_dir, new_name)
                        counter += 1
                    
                # Now move with the potentially modified destination path
                    shutil.move(item_path, dest_path)
                    # Log action
                    log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER', 
                        f"{item_path} → {dest_path}")  # Move to bin

                success_count += 1
                
                
                # Update automation folder reference if it was deleted
                if item_path == self.automation_folder:
                    self.automation_folder = None
                    conn = sqlite3.connect('docuvault.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET automation_folder = NULL WHERE username = ?', (self.username,))
                    conn.commit()
                    conn.close()
            except Exception as e:
                failed_items.append(f"{os.path.basename(item_path)}: {str(e)}")
        
        return {
            "success_count": success_count,
            "failed_items": failed_items,
            "skipped_items": skipped_items,
            "total": len(items)
        }
    
    def move_item(self, items, destination):
        """Move files/folders to destination"""
        dest_norm = os.path.normpath(destination)
        
        # Track success and failure
        success_count = 0
        failed_items = []
        skipped_items = []
        
        # Process each selected item
        for item_path in items:
            # SAFETY CHECK: Prevent moving to the same parent folder
            item_parent = os.path.dirname(os.path.normpath(item_path))
            if item_parent == dest_norm:
                skipped_items.append(f"{os.path.basename(item_path)} (already in destination)")
                continue
            
            try:
                base_name = os.path.basename(item_path)
                dest_path = os.path.join(destination, base_name)
                item_type = 'file' if os.path.isfile(dest_path) else 'folder'
                
                # Handle file conflicts
                if os.path.exists(dest_path):
                    if len(items) == 1:
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
                shutil.move(item_path, destination)
                log_action(self.username, 'MOVE', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} → {destination}")
                success_count += 1
            except Exception as e:
                failed_items.append(f"{os.path.basename(item_path)}: {str(e)}")
        # Clean up temporary attribute
        if hasattr(self, '_overwrite_all'):
            delattr(self, '_overwrite_all')

        return {
            "success_count": success_count,
            "failed_items": failed_items,
            "skipped_items": skipped_items,
            "total": len(items),
            "destination": destination
        }
    
    def copy_item(self, items, destination):
        """Copy files/folders to destination"""
        # Track success and failure
        success_count = 0
        failed_items = []
        
        # Process each selected item
        for item_path in items:
            try:
                base_name = os.path.basename(item_path)
                dest_path = os.path.join(destination, base_name)
                
                # Handle file conflicts
                if os.path.exists(dest_path):
                    # Generate unique name with counter
                    file_name, file_ext = os.path.splitext(base_name)
                    counter = 1
                    while os.path.exists(dest_path):
                        new_name = f"{file_name}_{counter}{file_ext}"
                        dest_path = os.path.join(destination, new_name)
                        counter += 1
                
                # Perform the copy
                if os.path.isfile(item_path):
                    shutil.copy2(item_path, dest_path)
                elif os.path.isdir(item_path):
                    shutil.copytree(item_path, dest_path)
                
                item_type = 'file' if os.path.isfile(item_path) else 'folder'
                log_action(self.username, 'COPY', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} copy→ {dest_path}")
                success_count += 1
            except Exception as e:
                failed_items.append(f"{os.path.basename(item_path)}: {str(e)}")

        return {
            "success_count": success_count,
            "failed_items": failed_items,
            "total": len(items),
            "destination": destination
        }
    
    def empty_bin(self):
        """Empty all items from the bin permanently"""
        try:
            items = os.listdir(self.bin_dir)
            if not items:
                return "The Bin is already empty."
        except Exception as e:
            return f"Could not access Bin: {e}"
        
        # Track results
        success_count = 0
        failed_items = []
        
        # Empty the bin
        for item in items:
            item_path = os.path.join(self.bin_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    item_type = 'file'
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path, onexc=remove_readonly)
                    item_type = 'folder'
                log_action(self.username, 'DELETE', 'FILE' if item_type=='file' else 'FOLDER', f"{item_path}", "Empty Bin")
                success_count += 1
            except Exception as e:
                failed_items.append(f"{item}: {e}")
        
        return {
            "success_count": success_count,
            "failed_items": failed_items,
            "total": len(items)
        }
    
    def restore_item(self, items, destination):
        """Restore files/folders from bin to destination"""
        if destination == self.bin_dir:
            return {
                "success": False,
                "message": "Cannot restore items back to the Bin",
                "success_count": 0,
                "failed_items": [],
                "total": len(items)
            }
        
        # Track success and failure
        success_count = 0
        failed_items = []
        
        # Process each selected item
        for item_path in items:
            try:
                base_name = os.path.basename(item_path)
                dest_path = os.path.join(destination, base_name)
                
                # Handle file conflicts
                if os.path.exists(dest_path):
                    if len(items) == 1:
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
                shutil.move(item_path, destination)
                
                item_type = 'file' if os.path.isfile(dest_path) else 'folder'
                log_action(self.username, 'RESTORE', 'FILE' if item_type=='file' else 'FOLDER', f"{item_path} → {destination}")
                success_count += 1
            except Exception as e:
                failed_items.append(f"{base_name}: {str(e)}")
        
        return {
            "success_count": success_count,
            "failed_items": failed_items,
            "total": len(items),
            "destination": destination
        }
