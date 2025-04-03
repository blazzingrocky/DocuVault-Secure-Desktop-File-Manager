import os
import time
import sqlite3
import nc_py_api
from tkinter import messagebox
from threading import Thread
from queue import Queue
from cryptography.fernet import Fernet
import bcrypt
import hashlib
import base64
from math import log
from database2 import log_action

class CloudManager:
    def __init__(self, username, gui_callback=None):
        """
        Initialize CloudManager.
        - username: current logged in user.
        - gui_callback: Reference to GUI object for progress and error updates.
        """
        self.username = username
        self.gui = gui_callback
        self.salt = None
        self.nc = None # Nextcloud connection instance
        self.search_queue = Queue() # Used for threaded search results
        self._init_db()
        self._load_credentials()

    def _init_db(self):
        """Create table for secure storage of cloud credentials if it doesn't exist."""
        with sqlite3.connect('docuvault.db') as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cloud_credentials
                (username TEXT PRIMARY KEY,
                server_url TEXT,
                encrypted_user BLOB,
                encrypted_pass BLOB,
                encryption_salt BLOB)
            ''')
            conn.commit()

    def _get_salt(self):
        """
        Retrieve or generate an encryption salt for this user.
        This salt is used in key derivation.
        """
        with sqlite3.connect('docuvault.db') as conn:
            result = conn.execute(
                'SELECT encryption_salt FROM cloud_credentials WHERE username = ?',
                (self.username,)
            ).fetchone()
        if not result:
            if self.salt:
                return self.salt
            new_salt = os.urandom(16)
            self.salt = new_salt
            return new_salt
        return result[0]

    def _get_encryption_key(self, master_password):
        """
        Derive a 32-byte key from the master_password using bcrypt's KDF.
        This key is then used (after further processing) for Fernet.
        """
        salt = self._get_salt()
        return bcrypt.kdf(
            password=master_password.encode(),
            salt=salt,
            desired_key_bytes=32,
            rounds=100
        )
    
    def schedule_ui(self, func, *args, delay=0):
        """
        Helper to safely schedule a GUI update call via .after().
        It retries if it catches a RuntimeError (main loop not running).
        """
        while True:
            try:
                self.gui.root.after(delay, lambda: func(*args))
                break
            except RuntimeError:
                time.sleep(0.05)
    
    def store_credentials(self, server_url, cloud_user, cloud_pass, master_password):
        """
        Securely store cloud credentials (server URL, username, and password) in the database.
        Credentials are encrypted using Fernet (key derived from master_password).
        """
        key = self._get_encryption_key(master_password)
        # Fernet requires a base64-encoded 32-byte key. We use SHA256 digest of our key.
        fernet_key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        cipher = Fernet(fernet_key)
        encrypted_user = cipher.encrypt(cloud_user.encode())
        encrypted_pass = cipher.encrypt(cloud_pass.encode())
        
        with sqlite3.connect('docuvault.db') as conn:
            cursor = conn.cursor()
            
            # First check if the username already exists
            cursor.execute("SELECT COUNT(*) FROM cloud_credentials WHERE username = ?", (self.username,))
            result = cursor.fetchone()
            
            # If the username doesn't exist (count is 0), insert the new record
            if result[0] == 0:
                conn.execute('''INSERT INTO cloud_credentials 
                            VALUES (?, ?, ?, ?, ?)''',
                            (self.username, server_url, encrypted_user,
                            encrypted_pass, self._get_salt()))
                conn.commit()
                messagebox.showinfo("Cloud Info", "Cloud credentials stored securely.")
            
            else:
                confirm = messagebox.askyesno("Cloud Info","Cloud credentials already exist. Do you want to update?")
                if confirm:
                    conn.execute('''UPDATE cloud_credentials 
                                SET server_url = ?, encrypted_user = ?, encrypted_pass = ?, encryption_salt = ?
                                WHERE username = ?''',
                                (server_url, encrypted_user, encrypted_pass, self._get_salt(), self.username))
                    conn.commit()
                    messagebox.showinfo("Cloud Info", "Cloud credentials stored securely.")

    def _load_credentials(self):
        """
        Load and decrypt stored credentials from the database.
        Then, initiate a Nextcloud connection.
        """
        with sqlite3.connect('docuvault.db') as conn:
            data = conn.execute(
                'SELECT server_url, encrypted_user, encrypted_pass FROM cloud_credentials WHERE username = ?',
                (self.username,)
            ).fetchone()
        if not data:
            messagebox.showinfo("Cloud Info", "No matching Cloud credentials found. Please setup Cloud.")
            return
        if data and self.gui:
            master_password = self.gui.get_master_password()
            if not master_password:
                return
            key = self._get_encryption_key(master_password)
            fernet_key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
            cipher = Fernet(fernet_key)
            try:
                self.server_url = data[0]
                self.nc_user = cipher.decrypt(data[1]).decode()
                self.nc_pass = cipher.decrypt(data[2]).decode()
                self.connect()
            except Exception as e:
                self.schedule_ui(self.gui.show_error, f"Decryption Error: Wrong master password")

    def connect(self):
        """
        Establish a connection to Nextcloud using the provided credentials.
        This runs in a separate thread to avoid blocking the GUI.
        """
        def connection_task():
            try:
                self.nc = nc_py_api.Nextcloud(
                    nextcloud_url=self.server_url,
                    nc_auth_user=self.nc_user,
                    nc_auth_pass=self.nc_pass
                )
                # Verify connection with a simple API call
                user_info = self.nc.user
                # Schedule GUI update on the main thread.
                self.schedule_ui(self.gui.update_progress, 100, f"Connected to Nextcloud! User ID: {user_info}", delay=0)
            except Exception as e:
                self.schedule_ui(self.gui.show_error, f"Connection failed: {str(e)}", delay=0)
                self.nc = None

        Thread(target=connection_task).start()
        if self.gui:
            self.schedule_ui(self.gui.show_progress, "Connecting to Nextcloud...", delay=0)

    def upload_file(self, local_path, remote_path):
        """
        Upload a file to Nextcloud using upload_stream() with simulated progress updates based on file size.
        - local_path: Path to the local file.
        - remote_path: Target remote path on the cloud (including file name).     
        """
        def upload_task():
            try:
                # Create remote directory if needed
                remote_dir = os.path.dirname(remote_path)
                if remote_dir and remote_dir != '/':
                    try:
                        self.nc.files.mkdir(remote_dir)
                    except:
                        # Directory might already exist
                        pass
                # Get file size in MB
                file_size_bytes = os.path.getsize(local_path)
                file_size_mb = file_size_bytes / (1024 * 1024)
                
                # Calculate estimated upload time based on provided data points
                # Using logarithmic model: time = a + b * log(size)
                if file_size_mb <= 0.1:  # ≤100KB
                    estimated_seconds = 1.0
                else:
                    # Constants derived from the provided data points
                    a = 1.0
                    b = 1.0
                    estimated_seconds = a + b * log(file_size_mb, 2)                    
                    # Cap at reasonable values
                    if estimated_seconds > 60:
                        estimated_seconds = 60
                
                # Start upload in separate thread
                upload_completed = False
                
                def do_upload():
                    nonlocal upload_completed
                    try:
                        with open(local_path, "rb") as f:
                            response = self.nc.files.upload_stream(remote_path, f)
                        upload_completed = True
                        log_action(self.username, 'CLOUD UPLOAD', 'FILE', f'{local_path} -> {remote_path}')
                    except Exception as e:
                        self.schedule_ui(self.gui.show_error, f"Upload failed: {str(e)}")
                
                upload_thread = Thread(target=do_upload)
                upload_thread.start()
                
                # Simulate progress updates
                start_time = time.time()                
                # Update every 200ms
                update_interval = 0.2
                steps = max(5, int(estimated_seconds / update_interval))
                
                for i in range(steps):
                    if upload_completed:
                        break                        
                    # Calculate simulated progress percentage (0-95%)
                    # Only go to 95% in simulation, real completion will push to 100%
                    progress = min(95, int((i / steps) * 100))                    
                    self.schedule_ui(self.gui.update_progress, progress, 
                                    f"Uploading {os.path.basename(local_path)}...")                    
                    
                    time.sleep(update_interval)                    
                    # If taking longer than expected, slow down updates
                    if i == steps - 1 and not upload_completed:
                        while not upload_completed and time.time() - start_time < 60:
                            time.sleep(0.5)               
                # Wait for actual completion
                upload_thread.join(timeout=60)                
                if upload_completed:
                    self.schedule_ui(self.gui.update_progress, 100, "Upload complete")
                else:
                    self.schedule_ui(self.gui.show_error, "Upload is taking longer than expected")
                    
            except Exception as e:
                self.schedule_ui(self.gui.show_error, f"Upload failed: {str(e)}")

        Thread(target=upload_task).start()
        if self.gui:
            self.schedule_ui(self.gui.show_progress, "Starting upload...")

    def download_file(self, remote_path, local_dir, custom_local_path=None):
        """
        Download a file from Nextcloud using download2stream() with approximate progress updates.
        - remote_path: The path to the file on the cloud.
        - local_dir: Local directory where the file will be saved.
        - custom_local_path: Optional custom path to save the file (for rename operations).
        """
        def download_task():
            # Determine the local path
            if custom_local_path:
                local_path = custom_local_path
            else:
                local_path = os.path.join(local_dir, os.path.basename(remote_path))
            try:
                # Use a fixed estimate based on the provided data
                estimated_seconds = 5.0  # Reasonable middle ground from the data points
                # Start download in separate thread
                download_completed = False
                
                def do_download():
                    nonlocal download_completed
                    try:
                        with open(local_path, "wb") as f:
                            self.nc.files.download2stream(remote_path, f)                            
                        download_completed = True
                        log_action(self.username, 'CLOUD DOWNLOAD', 'FILE', f'{remote_path} -> {local_path}')
                    except Exception as e:
                        self.schedule_ui(self.gui.show_error, f"Download failed: {str(e)}")
                        try:
                            if os.path.exists(local_path):
                                os.remove(local_path)
                        except:
                            pass
                
                download_thread = Thread(target=do_download)
                download_thread.start()
                
                # Simulate progress updates
                start_time = time.time()                                
                # Update every 200ms
                update_interval = 0.2
                steps = max(5, int(estimated_seconds / update_interval))
                
                for i in range(steps):
                    if download_completed:
                        break                        
                    # Calculate simulated progress percentage (0-95%)
                    progress = min(95, int((i / steps) * 100))                    
                    self.schedule_ui(self.gui.update_progress, progress, 
                                    f"Downloading {os.path.basename(remote_path)}...")
                    
                    time.sleep(update_interval)                    
                    # If taking longer than expected, slow down updates
                    if i == steps - 1 and not download_completed:
                        while not download_completed and time.time() - start_time < 60:
                            time.sleep(0.5)
                
                # Wait for actual completion
                download_thread.join(timeout=60)                
                if download_completed:
                    self.schedule_ui(self.gui.update_progress, 100, "Download complete")
                    self.schedule_ui(self.gui.update_file_list)
                else:
                    self.schedule_ui(self.gui.show_error, "Download is taking longer than expected")
                    
            except Exception as e:
                self.schedule_ui(self.gui.show_error, f"Download failed: {str(e)}")

        Thread(target=download_task).start()
        if self.gui:
            self.schedule_ui(self.gui.show_progress, "Starting download...")

    def delete_file(self, remote_path):
        """
        Delete a file from Nextcloud.
        - remote_path: The path to the file on the cloud.
        This runs in a separate thread.
        """
        def delete_task():
            try:
                self.nc.files.delete(remote_path)
                log_action(self.username, 'CLOUD DELETE', 'FILE', remote_path)
                if self.gui:
                    self.gui.show_info(f"Deleted {os.path.basename(remote_path)}")
            except Exception as e:
                if self.gui:
                    self.gui.show_error(f"Delete error: {str(e)}")

        Thread(target=delete_task).start()

    def search_files(self, search_term, callback):
        """
        Search for files on Nextcloud using the find() function.
        - search_term: The query string.
        - callback: Function to process results on the main thread.
        The results are queued and then passed to the callback.
        """
        def search_task():
            try:
                # Use the correct syntax for find: e.g., find(filter, path)
                results = self.nc.files.find(["like", "name", f"%{search_term}%"], "/DocuVault/")
                self.search_queue.put(results)
                if self.gui:
                    # Schedule processing of results on the main thread.
                    self.gui.root.after(100, lambda: self.process_search_queue(callback))
            except Exception as e:
                if self.gui:
                    self.gui.show_error(f"Search failed: {str(e)}")

        Thread(target=search_task).start()
        if self.gui:
            self.gui.show_progress("Searching cloud...")

    def process_search_queue(self, callback):
        """
        Process search results from the queue and call the provided callback with the result list.
        """
        while not self.search_queue.empty():
            results = self.search_queue.get()
            if callback and self.gui:
                callback(results)
        if self.gui:
            self.schedule_ui(self.gui.update_progress, 100, "Cloud search completed")
        return False
    
    def share_task(self, remote_path, permissions, password=None, expire_date=None):
        """
        Backend function to create a public share link for a file on Nextcloud.

        Args:
            remote_path (str): Path to the file on Nextcloud.
            permissions (int): Permissions for the share (1 = read-only, 3 = read-write).
            password (str, optional): Password to protect the share. Defaults to None.
            expire_date (datetime, optional): Expiration date for the share. Defaults to None.

        Returns:
            str: The public share URL if successful.
        """
        try:
            share_params = {
            'path': remote_path,
            'share_type': 3,  # 3 = public link
            'permissions': permissions
            }
            if password is not None:
                share_params['password'] = password
            if expire_date is not None:
                share_params['expire_date'] = expire_date
            # Create a public share link using Nextcloud API
            share = self.nc.files.sharing.create(**share_params)
            log_action(self.username, 'CLOUD SHARE', 'FILE', remote_path, share.url)
            # Extract and return the share URL
            return share.url

        except Exception as e:
            error_message = f"Failed to create a share link for {remote_path}: {str(e)}"
            if self.gui:
                self.schedule_ui(self.gui.show_error, error_message)
            return None


    def handle_error(self, error):
        """
        Centralized error handling. Maps error status codes to friendly messages.
        """
        error_messages = {
            404: "File not found on cloud",
            403: "Permission denied - check app password permissions",
            409: "Conflict - file may be locked",
            507: "Insufficient cloud storage",
            500: "Server error - try again later"
        }
        msg = error_messages.get(getattr(error, 'status_code', None), f"Cloud error: {str(error)}")
        if self.gui:
            self.gui.show_error(msg)
