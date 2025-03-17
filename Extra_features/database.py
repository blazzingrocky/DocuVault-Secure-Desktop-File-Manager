

from tkinter import filedialog, messagebox, simpledialog
import sqlite3
import bcrypt


def create_database():
    conn = None
    try:
        conn = sqlite3.connect('docuvault.db')
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
            )
        ''')
        
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
            )
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def get_db_connection():
    conn = sqlite3.connect('docuvault.db')
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def register_user(username, password, automation_folder):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if automation_folder:
            cursor.execute('INSERT INTO users (username, password, automation_folder) VALUES (?, ?, ?)',
                           (username, hashed, automation_folder))
        else:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                           (username, hashed))
        conn.commit()
        messagebox.showinfo("Registration", "User registered successfully!")
    except sqlite3.IntegrityError:
        messagebox.showerror("Registration Error", "Username already exists.")
    finally:
        conn.close()

def login_user(username, password):
    conn = get_db_connection()

    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return None  # Username not found
    if bcrypt.checkpw(password.encode('utf-8'), result[0]):
        return True
    else:
        return False
    
def log_action(username, action_type, item_type, item_path, details=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_activity 
        (username, action_type, item_type, item_path, details)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, action_type, item_type, item_path, details))
    conn.commit()
    conn.close()

def get_user_logs(username=None, limit=100):
    conn = get_db_connection()
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
    results = cursor.fetchall()
    conn.close()
    return results
