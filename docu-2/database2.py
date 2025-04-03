import threading
from queue import Queue
from tkinter import filedialog, messagebox, simpledialog
import sqlite3
import bcrypt

class DatabaseQueue:
    def __init__(self, db_path='docuvault.db'):
        self.queue = Queue()
        self.db_path = db_path
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
    
    def _process_queue(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        while True:
            task, args, callback = self.queue.get()
            try:
                result = task(conn, *args)
                if callback:
                    callback(True, result)
            except Exception as e:
                if callback:
                    callback(False, str(e))
            finally:
                self.queue.task_done()
    
    def execute(self, task, args=(), callback=None):
        """
        Add a task to the queue
        Returns a tuple (success, result) if callback is provided
        Otherwise returns None
        """
        result_container = [None, None]  # [success, result]
        
        def internal_callback(success, result):
            result_container[0] = success
            result_container[1] = result
            if callback:
                callback(success, result)
        
        self.queue.put((task, args, internal_callback))
        return result_container

# Create a global database queue instance
db_queue = DatabaseQueue()

# Modify existing functions to use the queue
def create_database():
    def task(conn):
        cursor = conn.cursor()
        # Enable foreign keys FIRST
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create users table FIRST
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            automation_folder TEXT
        )''')
        
        # Then create activity table with foreign key
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            username TEXT NOT NULL,
            action_type TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_path TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE
        )''')
        
        # Create logs table for file operations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            old_path TEXT NOT NULL,
            new_path TEXT,
            username TEXT,
            FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE
        )''')
        
        conn.commit()
        return True
    
    return db_queue.execute(task)

def get_db_connection():
    # This function is kept for backward compatibility
    conn = sqlite3.connect('docuvault.db')
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def register_user(username, password, automation_folder):
    def task(conn, username, password, automation_folder):
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor = conn.cursor()
        
        if automation_folder:
            cursor.execute('INSERT INTO users (username, password, automation_folder) VALUES (?, ?, ?)',
                          (username, hashed, automation_folder))
        else:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                          (username, hashed))
        
        conn.commit()
        return True
    
    def callback(success, result):
        if success:
            messagebox.showinfo("Registration", "User registered successfully!")
        else:
            messagebox.showerror("Registration Error", "Username already exists.")
    
    db_queue.execute(task, (username, password, automation_folder), callback)

def login_user(username, password):
    def task(conn, username, password):
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        
        if not result:
            return None  # Username not found
        
        if bcrypt.checkpw(password.encode('utf-8'), result[0]):
            return True
        else:
            return False
    
    result_container = db_queue.execute(task, (username, password))
    # Wait for result (this is synchronous for login)
    while result_container[0] is None:
        pass
    return result_container[1]

def log_action(username, action_type, item_type, item_path, details=None):
    def task(conn, username, action_type, item_type, item_path, details):
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO user_activity
        (username, action_type, item_type, item_path, details)
        VALUES (?, ?, ?, ?, ?)
        ''', (username, action_type, item_type, item_path, details))
        conn.commit()
        return True
    
    db_queue.execute(task, (username, action_type, item_type, item_path, details))

def get_user_logs(username=None, limit=100):
    def task(conn, username, limit):
        cursor = conn.cursor()
        query = '''
        SELECT timestamp, action_type, item_type, item_path, details
        FROM user_activity
        '''
        
        params = ()
        if username:
            query += ' WHERE username = ?'
            params = (username,)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params += (limit,)
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    result_container = db_queue.execute(task, (username, limit))
    # Wait for result (this is synchronous for getting logs)
    while result_container[0] is None:
        pass
    return result_container[1]

def log_file_operation(username, action, item_type,old_path, new_path=None):
    def task(conn, username, action, old_path, new_path):
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO logs
        (action, item_type,old_path, new_path, username)
        VALUES (?, ?, ?, ?)
        ''', (action, item_type,old_path, new_path, username))
        conn.commit()
        return True
    
    db_queue.execute(task, (username, action, old_path, new_path))

def delete_user_account(username):
    """Delete a user account and associated data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete user - foreign key cascade will handle activity records
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting account: {e}")
        return False
    finally:
        conn.close()

# def delete_user_logs(username):
#     """Delete all logs for a user"""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute('DELETE FROM logs WHERE username = ?', (username,))
#         conn.commit()
#         return True
#     except sqlite3.Error as e:
#         print(f"Error deleting logs: {e}")
#         return False
#     finally:
#         conn.close()

def delete_user_logs(username):
    """Delete all logs for a user from both logs and user_activity tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete from logs table
        cursor.execute('DELETE FROM logs WHERE username = ?', (username,))
        
        # Also delete from user_activity table
        cursor.execute('DELETE FROM user_activity WHERE username = ?', (username,))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting logs: {e}")
        return False
    finally:
        conn.close()

