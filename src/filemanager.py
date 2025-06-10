import os
import oschmod
import stat
import shutil
import time
import sqlite3
import subprocess
import json

from database import log_action,log_file_operation

from tkinter import messagebox
from datetime import datetime, timedelta

def remove_readonly(func, path, _):
    """Remove read-only attribute from file before operations"""
    try:
        os.chmod(path, stat.S_IWRITE) # Remove read-only flag
        func(path)
    except Exception as e:

        messagebox.showerror("Error", f"Error removing read-only attribute: {e}")


def restrict_access(path):
    """Restrict all access permissions to the specified file or directory."""
    try:
        # Use oschmod instead of os.chmod for cross-platform compatibility
        oschmod.set_mode(path, 0o000) # No permissions for anyone
    except Exception as e:

        messagebox.showerror("Error", f"Error restricting access: {e}")


def allow_access(path):
    """Allow all access permissions to the specified file or directory."""
    try:
        # Use oschmod instead of os.chmod for cross-platform compatibility
        oschmod.set_mode(path, 0o755) # rwx for owner, rx for group and others
    except Exception as e:

        messagebox.showerror("Error", f"Error allowing access: {e}")


class FileManager:
    def __init__(self, username, bin_dir,archive_dir):
        self.username = username
        self.bin_dir = bin_dir
        self.archive_dir = archive_dir
        self.automation_folder = self.get_automation_folder(username)

        self.db_connection = sqlite3.connect('filemanager.db', timeout=30.0)



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

    def get_frequently_accessed_files(self, threshold=1):
        current_time = time.time()
        frequent_files = []
        try:
            with open('file_access_log.json', 'r') as f:
                log = json.load(f)
                for file, access_time in log.items():
                    if current_time - access_time <= threshold * 3600 * 24 and os.path.exists(file):
                        frequent_files.append(file)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return frequent_files
    

    def update_file_access(self, file_path):
        current_time = time.time()
        try:
            with open('file_access_log.json', 'r+') as f:
                try:
                    log = json.load(f)
                except json.JSONDecodeError:
                    log = {}
                log[file_path] = current_time
                f.seek(0)
                f.truncate()
                json.dump(log, f)
        except FileNotFoundError:
            with open('file_access_log.json', 'w') as f:
                json.dump({file_path: current_time}, f)

    def apply_filters(self, item_path, extensions, date_limit, size_filter):
        if extensions and os.path.isfile(item_path):
            if os.path.splitext(item_path)[1].lower() not in extensions:
                return False
        if date_limit and os.path.exists(item_path):
            if datetime.fromtimestamp(os.path.getmtime(item_path)) < date_limit:
                return False
        if size_filter != "Any Size" and os.path.isfile(item_path):
            file_size = os.path.getsize(item_path)
            if size_filter == "Small (<1MB)" and file_size >= 1024*1024:
                return False
            elif size_filter == "Medium (1-100MB)" and (file_size < 1024*1024 or file_size > 100*1024*1024):
                return False
            elif size_filter == "Large (>100MB)" and file_size <= 100*1024*1024:
                return False
        return True



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

    # New function for archiving old files
    def archive_old_files(self, path,archive_age=30):
        """Archive files older than archive_age days"""
        results = {
            "success_count": 0,
            "failed_items": [],
            "skipped_items": []
        }
        
        current_time = time.time()
        
        try:
            for root, _, files in os.walk(path):
                # Skip bin and archive directories
                if self.bin_dir in root or self.archive_dir in root:
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    list_of_extensions = ['txt', 'pdf', 'jpg', 'jpeg', 'png', 'docx', 'xlsx', 
                                         'pptx', 'mp4', 'mp3', 'wav', 'avi', 'mkv', 'mov', 'flv', 'wmv']
                    
                    try:
                        # Check if file is older than archive_age days and has valid extension
                        # file_ext = os.path.splitext(file_path)[1].lower().strip('.')

                        if (current_time - os.path.getmtime(file_path) > archive_age*3600*24 and 

                            any(file_path.split('.')[-1] for each in list_of_extensions)):
                            confirm=messagebox.askyesno("Confirm Archive", f"Are you sure you want to archive {file}?")
                            if confirm:
                            # Create destination path
                                archive_dest = os.path.join(self.archive_dir, file)
    
                                # Handle name conflicts
                                counter = 1
                                base_name, ext = os.path.splitext(file)
                                while os.path.exists(archive_dest):
                                    new_name = f"{base_name}_{counter}{ext}"
                                    archive_dest = os.path.join(self.archive_dir, new_name)
                                    counter += 1
                                
                                # Move file to archive
                                shutil.move(file_path, archive_dest)
                                log_action(self.username, 'ARCHIVE', 'FILE', f"{file_path} â†’ {archive_dest}")
                                results["success_count"] += 1
                            else:
                                os.utime(file_path,(current_time, current_time))
                                results["skipped_items"].append(file_path)
                            
                    except Exception as e:
                        results["failed_items"].append(f"{file}: {str(e)}")
                        
        except Exception as e:
            results["failed_items"].append(f"Error scanning files: {str(e)}")
        
        return results

    # Function to empty archive
    def empty_archive(self):
        """Empty all items from the archive permanently"""
        try:
            items = os.listdir(self.archive_dir)
            if not items:
                return "The Archive is already empty."
        except Exception as e:
            return f"Could not access Archive: {e}"
            
        # Track results
        success_count = 0
        failed_items = []
        
        # Empty the bin
        for item in items:
            item_path = os.path.join(self.archive_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    item_type = 'file'
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path, onexc=remove_readonly)
                    item_type = 'folder'
                    
                log_action(self.username, 'DELETE', 'FILE' if item_type=='file' else 'FOLDER', f"{item_path}", "Empty Archive")
                success_count += 1
                
            except Exception as e:
                failed_items.append(f"{item}: {e}")
                
        return {
            "success_count": success_count,
            "failed_items": failed_items,
            "total": len(items)
        }


    # Functions for tracking file access and backups
    def update_file_access(self, file_path):
        """Track file access time for determining frequently accessed files"""
        current_time = time.time()
        log_path = os.path.join(os.path.expanduser('~'), 'file_access_log.json')
        
        try:
            try:
                with open(log_path, 'r') as f:
                    try:
                        log = json.load(f)
                    except json.JSONDecodeError:
                        log = {}
            except FileNotFoundError:
                log = {}
            
            log[file_path] = current_time
            
            with open(log_path, 'w') as f:
                json.dump(log, f)
                
            return True
        except Exception as e:
            print(f"Error updating file access log: {e}")
            return False

    def get_frequently_accessed_files(self, threshold=1):
        """Get list of files accessed within the threshold period (days)"""
        current_time = time.time()
        log_path = os.path.join(os.path.expanduser('~'), 'file_access_log.json')
        
        try:
            with open(log_path, 'r') as f:
                try:
                    log = json.load(f)
                    # Return files accessed within threshold days
                    return [file for file, access_time in log.items()
                           if current_time - access_time <= threshold * 24 * 3600
                           and os.path.exists(file)]
                except json.JSONDecodeError:
                    return []
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error getting frequently accessed files: {e}")
            return []

    def backup_frequent_files(self, cloud_manager, threshold=1):
        """Backup frequently accessed files to cloud storage"""
        if not cloud_manager or not cloud_manager.nc:
            return {
                "success": False,
                "message": "No cloud connection available"
            }
        
        frequent_files = self.get_frequently_accessed_files(threshold)
        
        if not frequent_files:
            return {
                "success": True,
                "message": "No frequently accessed files to backup"
            }
        
        results = {
            "success_count": 0,
            "failed_items": [],
            "total": len(frequent_files)
        }
        
        # Try to create backup directory in cloud
        try:
            cloud_manager.nc.files.mkdir("/DocuVault/Backup")
        except:
            # Directory might already exist
            pass
        
        # Upload each file to cloud
        for file_path in frequent_files:
            if os.path.isfile(file_path):
                try:
                    remote_path = f"/DocuVault/Backup/{os.path.basename(file_path)}"
                    cloud_manager.upload_file(file_path, remote_path)
                    log_action(self.username, 'BACKUP', 'FILE', f"{file_path} â†’ Cloud:{remote_path}")
                    results["success_count"] += 1
                except Exception as e:
                    results["failed_items"].append(f"{os.path.basename(file_path)}: {str(e)}")
        
        return results


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
            log_action(self.username, 'RENAME', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} â†’ {new_path}")
            return True, new_path
        except Exception as e:
            return False, f"Could not rename item: {e}"


    def get_available_apps(self, file_path):
        """Get list of available applications to open a file"""
        file_ext = os.path.splitext(file_path)[1].lower()
        available_apps = []
        
        if os.name == 'nt': # Windows implementation
            # Add Default option first
            available_apps.append(("Default (System Default)", None)) # None indicates system default
            
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
                        
        elif os.name == 'posix': # Linux/macOS implementation
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
                
                # Track file access for frequent files feature
                self.update_file_access(item_path)
                return True, "File opened successfully"
                
            elif os.path.isdir(item_path):
                return True, item_path # Signal to navigate to this directory
                
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
                return True, file_path
                
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
                return True, folder_path
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
            
            if self.bin_dir and os.path.normpath(item_path) == os.path.normpath(self.bin_dir):
                skipped_items.append(f"{os.path.basename(item_path)} (bin folder)")
                continue

            try:
                if permanently:
                    # Permanent deletion
                    if item_type == 'file':
                        os.remove(item_path)
                    elif item_type == 'folder':
                        shutil.rmtree(item_path, onexc=remove_readonly)
                        
                    log_action(self.username, 'DELETE', item_type.upper(), item_path, "Permanent Deletion")
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
                    allow_access(self.bin_dir)
                    shutil.move(item_path, dest_path)
                    restrict_access(self.bin_dir)
                    # Log action
                    log_action(self.username, 'DELETE', 'FILE' if item_type == 'file' else 'FOLDER',
                              f"{item_path} -> {dest_path}", "Move to Bin")
                    
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

                item_type = 'file' if os.path.isfile(item_path) else 'folder'

                
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
                            if response is None: # Cancel
                                break
                            elif response: # Yes
                                self._overwrite_all = True
                            else: # No
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
                success_count += 1

                log_action(self.username, 'MOVE', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} -> {destination}")
                

                
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
                success_count += 1
            
                item_type = 'file' if os.path.isfile(item_path) else 'folder'

                log_action(self.username, 'COPY', 'FILE' if item_type == 'file' else 'FOLDER', f"{item_path} copy-> {dest_path}")
                

                
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
        if (os.path.basename(self.bin_dir) in os.path.normpath(destination).split(os.path.sep)):
            return {
                "success": False,
                "success_count": 0,
                "failed_items": ["Cannot restore items back to the Bin"],
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
                            if response is None: # Cancel
                                break
                            elif response: # Yes
                                self._overwrite_all = True
                            else: # No
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
                success_count += 1
                item_type = 'file' if os.path.isfile(dest_path) else 'folder'
                log_action(self.username, 'RESTORE', 'FILE' if item_type=='file' else 'FOLDER', f"{item_path} -> {destination}")
                
            except Exception as e:
                failed_items.append(f"{base_name}: {str(e)}")
                
        return {
            "success_count": success_count,
            "failed_items": failed_items,
            "total": len(items),
            "destination": destination
        }