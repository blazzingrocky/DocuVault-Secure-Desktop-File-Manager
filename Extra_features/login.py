import tkinter as tk
from tkinter import messagebox, filedialog
import os
from tkinter import ttk
from PIL import Image, ImageTk
from database import create_database, register_user, login_user
from automation import AutomationWindow

from filemanager import FileManagerGUI
from utility import CustomDirectoryDialog

class LoginPage(tk.Tk):
    def __init__(self):
        super().__init__()

        
        # Configure window
        self.title("DocuVault")
        self.geometry("400x550")
        self.configure(bg="#f5f5f5")
        self.resizable(False, False)
        
        # Set app icon if available
        try:
            self.iconbitmap("AppIcon\\DocuVault-icon.ico")
        except:
            pass
        
        # Apply modern style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure styles
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('TLabel', background='#f5f5f5', font=('Segoe UI', 10))
        self.style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))
        self.style.configure('TEntry', font=('Segoe UI', 11))
        self.style.configure('TButton', font=('Segoe UI', 11))
        self.style.map('Accent.TButton',
            background=[('active', '#3755be'), ('!active', '#4267b2')],
            foreground=[('active', 'white'), ('!active', 'white')])
        
        # Create main container
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill="both", padx=40, pady=30)
        
        # Logo or app name
        logo_frame = ttk.Frame(main_frame)
        logo_frame.pack(fill="x", pady=(0, 25))
        
        # Try to load logo image, use text as fallback
        try:
            logo_img = Image.open("AppIcon\\DocuVault-img.png")
            logo_img = logo_img.resize((100, 100), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_img)
            logo_label = ttk.Label(logo_frame, image=logo_photo)
            logo_label.image = logo_photo  # Keep a reference
            logo_label.pack(anchor="center")
        except:
            # Fallback to text header
            logo_label = ttk.Label(logo_frame, text="DocuVault", style="Header.TLabel")
            logo_label.pack(anchor="center")
        
        # Welcome text
        welcome_label = ttk.Label(main_frame, 
                              text="Welcome back! Please sign in", 
                              font=('Segoe UI', 12))
        welcome_label.pack(fill="x", pady=(0, 15))
        
        # Username field
        username_frame = ttk.Frame(main_frame)
        username_frame.pack(fill="x", pady=5)
        
        username_label = ttk.Label(username_frame, text="Username", anchor="w")
        username_label.pack(fill="x")
        
        self.username_entry = ttk.Entry(username_frame, font=('Segoe UI', 11))
        self.username_entry.pack(fill="x", pady=5)
        
        # Password field
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill="x", pady=5)
        
        password_label = ttk.Label(password_frame, text="Password", anchor="w")
        password_label.pack(fill="x")
        
        self.password_entry = ttk.Entry(password_frame, show="•", font=('Segoe UI', 11))
        self.password_entry.pack(fill="x", pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=15)
        
        login_button = ttk.Button(button_frame, text="Sign In", 
                                style="Accent.TButton", command=self.login_submit)
        login_button.pack(fill="x", ipady=4, pady=5)
        
        register_button = ttk.Button(button_frame, text="Create Account", 
                                   command=self.register_user)
        register_button.pack(fill="x", ipady=5, pady=5)
        
        # Footer text
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill="x", pady=10)
        footer_label = ttk.Label(footer_frame, 
                              text="© 2025 DocuVault File Management", 
                              font=('Segoe UI', 8))
        footer_label.pack()
        
        # Set initial focus
        self.username_entry.focus()        
        # Bind Enter key to login
        self.bind('<Return>', lambda event: self.login_submit())
        
    def login_submit(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        login_result = login_user(username, password)
        
        if login_result is None:
            messagebox.showinfo("Login Failed", "No user found with this username. Please register first.")
        elif login_result:
            self.destroy()
            app = FileManagerGUI(username)
            app.run()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

            
    def register_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Registration Failed", "Username and password cannot be empty.")
            return
            
        setup_automation = messagebox.askyesno("Automation Setup", "Do you want to set up automation?")
        
        if setup_automation:
            dest_dialog = CustomDirectoryDialog(self, os.getcwd())
            self.wait_window(dest_dialog)
            automation_folder = dest_dialog.selected_path

            if automation_folder:
                register_user(username, password, automation_folder)
            else:
                messagebox.showinfo("Registration", "Registration cancelled, no automation folder selected.")
        else:
            register_user(username, password, None)

