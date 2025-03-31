import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk, Menu
import os
import sqlite3
import time
import threading
from datetime import timedelta,datetime
import subprocess
from newfilemanager2 import FileManager, allow_access, restrict_access
from automation import AutomationWindow
from utility import CustomDirectoryDialog, compare_path
from database import log_action, get_user_logs
from cloud import CloudManager
import schedule

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

class LogViewer(tk.Toplevel):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.title("Activity Logs")
        self.tree = ttk.Treeview(self, columns=('Time', 'Action', 'Type', 'Path', 'Details'))
        
        self.tree.heading('#0', text='ID')
        self.tree.column('#0', width=50)
        for col in ('Time', 'Action', 'Type', 'Path', 'Details'):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        logs = get_user_logs(username)
        for log in logs:
            self.tree.insert('', 'end', values=log)
        
        self.tree.pack(expand=True, fill='both')
class Dashboard:
    def __init__(self, parent):
        self.parent = parent
        self.dashboard_window = tk.Toplevel(parent.root)
        self.dashboard_window.title("DocuVault Dashboard")
        self.dashboard_window.geometry("600x500")

        icon_path = os.path.join("AppIcon", "Docu-icon.ico")
        # icon = Image.open(icon_path)
        # photo = ImageTk.PhotoImage(icon)
        # self.dashboard_window.iconphoto(False, photo)
        # try:
        #     self.dashboard_window.iconbitmap("AppIcon\\Docu-icon.ico")
        # except Exception as e:
        #     print(f"Error setting icon: {e}")

        main_frame = ttk.Frame(self.dashboard_window, padding="10")
        main_frame.pack(expand=True, fill="both")

        # Welcome message
        welcome_label = ttk.Label(main_frame, text=f"Hello, {self.parent.username},\nWelcome to DocuVault!", 
                                  font=("Segoe UI", 14, "bold"), anchor="center", justify="center")
        welcome_label.pack(fill="x", pady=(0, 15))

        # Buttons for different locations
        home_btn = ttk.Button(main_frame, text="Home", 
                              command=lambda: self.go_to_directory(os.path.expanduser("~")))
        home_btn.pack(pady=5)

        desktop_btn = ttk.Button(main_frame, text="Desktop", 
                                 command=lambda: self.go_to_directory(r"C:\Users\shara\OneDrive\Attachments\Desktop"))
        desktop_btn.pack(pady=5)

        cwd_btn = ttk.Button(main_frame, text="Current Working Directory", 
                             command=lambda: self.go_to_directory(os.getcwd()))
        cwd_btn.pack(pady=5)

        self.update_file_counts(main_frame)
        # self.create_visualization_buttons(main_frame)
        chart_btn = ttk.Button(main_frame, text="File Type Distribution Chart", command=self.show_file_type_chart)
        chart_btn.pack(pady=10)
    

    def create_file_type_chart(file_types):
        """
        Create a pie chart using Matplotlib to display file type distribution.

        Parameters:
            file_types (dict): A dictionary where keys are file types (extensions) and values are their counts.

        Returns:
            None: Displays the pie chart.
        """
        # Extract data for the pie chart
        labels = list(file_types.keys())
        sizes = list(file_types.values())

        # Create the pie chart
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title("File Type Distribution")

        # Display the chart
        plt.show()

    def show_file_type_chart(self):
        """
        Show the File Type Distribution Chart in a new window.
        """
        file_types = self.parent.count_files_by_type(self.parent.current_dir)
        
        # Convert counts to a dictionary for chart creation
        file_types_dict = {
            ".txt": file_types[0],
            ".jpg": file_types[1],
            ".pdf": file_types[2]
            # Add more extensions as needed
        }
        
        create_file_type_chart(file_types_dict)
    def go_to_directory(self, path):
        self.parent.initialize_main_window(path)
        self.dashboard_window.destroy()

    def update_file_counts(self, frame):
        home_dir = os.path.expanduser("~")
        text_count, image_count, video_count = self.parent.count_files_by_type(home_dir)

        ttk.Label(frame, text=f"Text Files: {text_count}", font=("Segoe UI", 11)).pack(pady=5)
        ttk.Label(frame, text=f"Image Files: {image_count}", font=("Segoe UI", 11)).pack(pady=5)
        ttk.Label(frame, text=f"Video Files: {video_count}", font=("Segoe UI", 11)).pack(pady=5)

class FileManagerGUI:
    def __init__(self, username):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main window initially
        self.username = username
        self.current_dir = os.getcwd()

        self.sort_by = "name"
        self.archive_mode = tk.BooleanVar(value=False)
        self.archive_age = tk.IntVar(value=30)

        self.bin_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Bin')

        os.makedirs(self.bin_dir, exist_ok=True)
        restrict_access(self.bin_dir)
        self.archive_dir = os.path.join(os.path.expanduser('~'), 'DocuVault_Archive')
        os.makedirs(self.archive_dir, exist_ok=True)
        self.search_results_window = None
        self.cloud = None  # Placeholder for cloud manager
        self.progress_window = None
        self.file_manager = FileManager(username, self.bin_dir,self.archive_dir)
        self.automation_folder = self.file_manager.automation_folder

        #Initialize cloud
        self.root.after(100, self.initialize_cloud)
        self.create_widgets()

        # Show dashboard immediately
        self.show_dashboard()

    def show_dashboard(self):
        Dashboard(self)

    def initialize_main_window(self, initial_dir):
        self.current_dir = initial_dir
        self.root.deiconify()  # Show the main window
        self.root.title("DocuVault: Secure Desktop File Manager")
        self.root.geometry("800x400")

        try:
            self.root.iconbitmap("AppIcon\\Docu-icon.ico")
        except Exception as e:
            pass

        self.update_file_list()
            
        schedule.every().day.at("03:00").do(self.backup_frequent_files)

        self.scheduler_thread = threading.Thread(target=self.run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        # Delay cloud initialization until the window is mapped.
    def count_files_by_type(self, directory):
        text_extensions = ['.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv']

        text_count = image_count = video_count = 0

        for root, _, files in os.walk(directory):
            for file in files:
                _, ext = os.path.splitext(file.lower())
                if ext in text_extensions:
                    text_count += 1
                elif ext in image_extensions:
                    image_count += 1
                elif ext in video_extensions:
                    video_count += 1

        return text_count, image_count, video_count
    def create_file_type_chart(self):
        file_types = self.get_file_type_distribution()
        fig = px.pie(values=list(file_types.values()), names=list(file_types.keys()), title="File Type Distribution")
        return fig

    def get_file_type_distribution(self):
        file_types = {}
        for root, _, files in os.walk(self.current_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                file_types[ext] = file_types.get(ext, 0) + 1
        return file_types

#     def go_to_home(self):
#         self.current_dir = os.path.expanduser("~")
# # =======
# #         self.create_widgets()
# # >>>>>>> main
#         self.update_file_list()

#     def go_desktop(self):
#         self.current_dir = os.path.join(os.path.expanduser("~"), "Desktop")
#         self.update_file_list()

#     def go_to_current_directory(self):
#         self.current_dir = os.getcwd()
#         self.update_file_list()
    def run_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def initialize_cloud(self):
        self.cloud = CloudManager(self.username, gui_callback=self)
        self.update_cloud_status('disconnected')
    def user_activity(self, event=None):
        """Reset the timer whenever user activity is detected"""
        self.last_activity_time = time.time() * 1000
        self.reset_inactivity_timer()

    def reset_inactivity_timer(self):
        """Reset and restart the inactivity timer"""
        # Cancel any existing timer
        if self.activity_timer_id:
            self.root.after_cancel(self.activity_timer_id)
        
        # Start a new timer
        self.activity_timer_id = self.root.after(self.inactivity_timeout, self.logout_due_to_inactivity)

    def logout_due_to_inactivity(self):
        """Log out the user when inactivity timeout is reached"""
        messagebox.showinfo("Automatic Logout", "You have been logged out due to 30 minutes of inactivity.")
        self.sign_out(time_out=True)

    def archive_old_files(self):
        archived_files = self.file_manager.archive_old_files(self.current_dir,self.archive_age.get())
        if(archived_files["success_count"]>0):
            messagebox.showinfo("Archive", f"Archived {archived_files['success_count']} files.")
        self.update_file_list()
    def go_to_archive(self):
        allow_access(self.archive_dir)
        self.current_dir = self.archive_dir
        
        self.update_file_list()
    def toggle_archive_options(self):
        if self.archive_mode.get():
            schedule.every().day.at("02:00").do(self.archive_old_files)
            for child in self.age_frame.winfo_children():
                child.configure(state='normal')
        else:
            for child in self.age_frame.winfo_children():
                child.configure(state='disabled')

    def empty_archive(self):
        confirm = messagebox.askyesno("Confirm Empty Bin", "Are you sure you want to permanently delete all items in the Archive?")
        if confirm:
            result = self.file_manager.empty_archive()
            if isinstance(result, dict):
                if result["success_count"] > 0:
                    messagebox.showinfo("Success", f"Successfully deleted {result['success_count']} item(s) from the Archive")
                if result["failed_items"]:
                    failed_msg = "\n".join(result["failed_items"])
                    messagebox.showerror("Error", f"Failed to delete some items:\n{failed_msg}")
            else:
                messagebox.showinfo("Info", result)
        self.update_file_list()
    def backup_frequent_files(self):
        frequent_files = self.file_manager.get_frequently_accessed_files()
        if not self.cloud or not self.cloud.nc:
            if self.cloud:
                self.cloud._load_credentials()
                
            if not self.cloud or not self.cloud.nc:
                log_action(self.username, 'ERROR', 'SYSTEM', 
                        "Cloud backup failed: No connection")
                return
        
        if not frequent_files:
            log_action(self.username, 'BACKUP', 'SYSTEM', 
                    "No frequently accessed files to backup")
            return
            
        # Create backup directory in cloud
        try:
            self.cloud.nc.files.mkdir("/DocuVault/Backup")
        except:
            # Directory might already exist
            pass
            
        # Upload each file to cloud
        for file_path in frequent_files:
            if os.path.isfile(file_path):
                try:
                    remote_path = f"/DocuVault/Backup/{os.path.basename(file_path)}"
                    self.cloud.upload_file(file_path, remote_path)
                    log_action(self.username, 'BACKUP', 'FILE', 
                            f"{file_path} → Cloud:{remote_path}")
                except Exception as e:
                    log_action(self.username, 'ERROR', 'FILE', 
                            f"Backup failed for {file_path}: {str(e)}")
    def search_files(self):
        original_dir = self.current_dir
        
        if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
            self.search_results_window.destroy()
        
        self.search_results_window = tk.Toplevel(self.root)
        self.search_results_window.title("Search Files")
        self.search_results_window.geometry("800x600")
        
        # Create search frame at top
        search_frame = ttk.Frame(self.search_results_window, padding=10)
        search_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Search bar
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        search_button = ttk.Button(search_frame, text="Search", command=self.perform_search)
        search_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Filter options frame
        filter_frame = ttk.LabelFrame(self.search_results_window, text="Filter Options", padding=10)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # File type filter
        ttk.Label(filter_frame, text="File Type:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.file_type_var = tk.StringVar()
        file_types = ["All Files", "Documents (.txt, .pdf, .doc, .ppt)", "Images (.jpg, .png, .gif)", "Videos (.mp4, .avi, .mov)", "Audio (.mp3, .wav)"]
        file_type_combo = ttk.Combobox(filter_frame, textvariable=self.file_type_var, values=file_types, width=25, state='readonly')
        file_type_combo.current(0)
        file_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Date modified filter
        ttk.Label(filter_frame, text="Date Modified:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.date_var = tk.StringVar()
        date_options = ["Any Time", "Today", "This Week", "This Month", "This Year"]
        date_combo = ttk.Combobox(filter_frame, textvariable=self.date_var, values=date_options, width=15, state='readonly')
        date_combo.current(0)
        date_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Size filter
        ttk.Label(filter_frame, text="Size:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.size_var = tk.StringVar()
        size_options = ["Any Size", "Small (<1MB)", "Medium (1-100MB)", "Large (>100MB)"]
        size_combo = ttk.Combobox(filter_frame, textvariable=self.size_var, values=size_options, width=25, state='readonly')
        size_combo.current(0)
        size_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Search location
        ttk.Label(filter_frame, text="Search In:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.location_var = tk.StringVar(value=self.current_dir)
        location_entry = ttk.Entry(filter_frame, textvariable=self.location_var, width=30, state='readonly')
        location_entry.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Browse button
        def browse_folder():
            dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
            self.root.wait_window(dest_dialog)  # Wait for dialog to close
            return dest_dialog.selected_path
        
        browse_button = ttk.Button(filter_frame, text="...", width=3, 
                                command=lambda: self.location_var.set(browse_folder()))
        browse_button.grid(row=1, column=4, padx=2, pady=5)
        
        # Reset filters button
        reset_button = ttk.Button(filter_frame, text="Reset Filters", command=self.reset_search_filters)
        reset_button.grid(row=1, column=5, padx=5, pady=5)
        
        # Create the search results treeview
        results_frame = ttk.Frame(self.search_results_window)
        results_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Add a label for results count
        self.results_count_label = ttk.Label(results_frame, text="Results: 0 items found")
        self.results_count_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create treeview with scrollbars
        self.search_tree = ttk.Treeview(results_frame)
        self.search_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.search_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.search_tree.configure(yscrollcommand=vsb.set)
        
        # Configure treeview columns
        self.search_tree["columns"] = ("name", "path", "type", "size", "modified")
        self.search_tree.column("#0", width=40, minwidth=40)  # Icon column
        self.search_tree.column("name", width=200, minwidth=100)
        self.search_tree.column("path", width=300, minwidth=100)
        self.search_tree.column("type", width=100, minwidth=80)
        self.search_tree.column("size", width=100, minwidth=80)
        self.search_tree.column("modified", width=150, minwidth=100)
        
        self.search_tree.heading("#0", text="")
        self.search_tree.heading("name", text="Name")
        self.search_tree.heading("path", text="Path")
        self.search_tree.heading("type", text="Type")
        self.search_tree.heading("size", text="Size")
        self.search_tree.heading("modified", text="Date Modified")
        
        # Bind events
        self.search_tree.bind("<Double-1>", self.on_search_double_click)
        self.search_tree.bind("<Button-3>", self.show_search_context_menu)
        self.search_entry.bind("<Return>", lambda e: self.perform_search())
        
        # Set focus to search entry
        self.search_entry.focus_set()
        
        # Add status bar
        status_bar = ttk.Frame(self.search_results_window)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=2)
        self.search_status = ttk.Label(status_bar, text="Search for files...")
        self.search_status.pack(side=tk.LEFT, padx=10)
        
        # Initialize empty results
        self.local_results_found = False
        self.search_results = []

    def perform_search(self):
        """Execute search with current filters"""
        search_term = self.search_entry.get()
        if not search_term:
            messagebox.showinfo("Search", "Please enter a search term")
            return
        
        # Clear previous results
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        # Update status
        self.search_status.config(text="Searching...")
        self.search_results_window.update_idletasks()
        
        # Get filter values
        search_dir = self.location_var.get()
        file_type = self.file_type_var.get()
        date_filter = self.date_var.get()
        size_filter = self.size_var.get()
        
        # Convert file type filter to extensions
        extensions = []
        if file_type == "Documents (.txt, .pdf, .doc, .ppt)":
            extensions = ['.txt', '.pdf', '.doc', '.docx', '.rtf', '.odt', '.ppt', '.pptx', '.xls', '.xlsx']
        elif file_type == "Images (.jpg, .png, .gif)":
            extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        elif file_type == "Videos (.mp4, .avi, .mov)":
            extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
        elif file_type == "Audio (.mp3, .wav)":
            extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma']
        
        # Get current time for date filtering
        current_time = datetime.now()
        date_limit = None
        
        if date_filter == "Today":
            date_limit = current_time - timedelta(days=1)
        elif date_filter == "This Week":
            date_limit = current_time - timedelta(days=7)
        elif date_filter == "This Month":
            date_limit = current_time - timedelta(days=30)
        elif date_filter == "This Year":
            date_limit = current_time - timedelta(days=365)
        
        # Track results
        self.search_results = []
        self.local_results_found = False
        
        # Start the search
        self.recursive_search_with_filters(search_dir, search_term, extensions, date_limit, size_filter)
        
        # Update results count
        result_count = len(self.search_tree.get_children())
        self.results_count_label.config(text=f"Results: {result_count} items found")
        
        # Display message if no results found
        if not self.local_results_found:
            self.search_tree.insert("", "end", text="", values=("No matching results found", "", "", "", ""))
        
        # Update status
        self.search_status.config(text="Search completed")
        
        # Ask about cloud search
        if messagebox.askyesno("Cloud Search", "Search in Nextcloud storage?"):
            if self.cloud and self.cloud.nc:
                self.cloud.search_files(search_term, callback=self.display_cloud_results)
            else:
                messagebox.showinfo("Cloud Search", "Please connect to cloud first")
        
        # Bring search window back to focus
        self.search_results_window.lift()
        self.search_results_window.focus_set()
        
        # Set focus to search entry
    def recursive_search_with_filters(self, start_dir, search_term, extensions, date_limit, size_filter):
        results = []
        try:
            items = os.listdir(start_dir)
        except PermissionError:
            return results
        except Exception:
            return results

        for item in items:
            item_path = os.path.join(start_dir, item)
            try:
                # Skip if doesn't match search term
                if search_term.lower() not in item.lower():
                    # Still check subdirectories even if parent doesn't match
                    if os.path.isdir(item_path):
                        self.recursive_search_with_filters(item_path, search_term, extensions, date_limit, size_filter)
                    continue
                
                # Apply file type filter
                if extensions and os.path.isfile(item_path):
                    file_ext = os.path.splitext(item_path)[1].lower()
                    if file_ext not in extensions:
                        continue
                
                # Apply date filter
                if date_limit and os.path.exists(item_path):
                    mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    if mod_time < date_limit:
                        continue
                
                # Apply size filter
                if size_filter != "Any Size" and os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    if size_filter == "Small (<1MB)" and file_size >= 1024*1024:
                        continue
                    elif size_filter == "Medium (1-100MB)" and (file_size < 1024*1024 or file_size > 100*1024*1024):
                        continue
                    elif size_filter == "Large (>100MB)" and file_size <= 100*1024*1024:
                        continue
                
                # Item passed all filters, add to results
                self.add_search_result(item, item_path)
                self.local_results_found = True
                
                # Continue searching in subdirectories
                if os.path.isdir(item_path):
                    self.recursive_search_with_filters(item_path, search_term, extensions, date_limit, size_filter)
            except PermissionError:
                continue
            except Exception:
                continue
    def add_search_result(self, name, path):
        """Add an item to the search results tree"""
        try:
            # Determine file type
            if os.path.isdir(path):
                item_type = "Folder"
                icon = "📁"
                size_str = ""
            else:
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.txt', '.pdf', '.doc', '.docx', '.rtf']:
                    item_type = f"Document ({ext})"
                    icon = "📄"
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    item_type = f"Image ({ext})"
                    icon = "🖼️"
                elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                    item_type = f"Video ({ext})"
                    icon = "🎬"
                elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
                    item_type = f"Audio ({ext})"
                    icon = "🎵"
                else:
                    item_type = f"File ({ext})"
                    icon = "📄"
                
                # Format size
                size_bytes = os.path.getsize(path)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024*1024:
                    size_str = f"{size_bytes/1024:.1f} KB"
                elif size_bytes < 1024*1024*1024:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"
                else:
                    size_str = f"{size_bytes/(1024*1024*1024):.1f} GB"
            
            # Format date
            mod_time = datetime.fromtimestamp(os.path.getmtime(path))
            date_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Add to treeview
            self.search_tree.insert("", "end", text=icon, values=(name, path, item_type, size_str, date_str))
            
        except Exception as e:
            pass
    def reset_search_filters(self):
        """Reset all search filters to defaults"""
        self.file_type_var.set("All Files")
        self.date_var.set("Any Time")
        self.size_var.set("Any Size")
        self.search_entry.delete(0, tk.END)
        
        # Clear results
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        self.results_count_label.config(text="Results: 0 items found")
        self.search_status.config(text="Filters reset")

    def execute_search(self):
        search_term = self.search_entry.get()
        file_type = self.file_type_var.get()
        date_filter = self.date_var.get()
        size_filter = self.size_var.get()

        extensions = self.get_extensions_for_file_type(file_type)
        date_limit = self.get_date_limit(date_filter)

        results = self.file_manager.recursive_search_with_filters(self.current_dir, search_term, extensions, date_limit, size_filter)

        self.populate_search_results(results)

    def get_extensions_for_file_type(self, file_type):
        if file_type == "Documents":
            return ['.txt', '.pdf', '.doc', '.docx', '.rtf', '.odt']
        elif file_type == "Images":
            return ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        elif file_type == "Videos":
            return ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
        elif file_type == "Audio":
            return ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma']
        else:
            return []

    def get_date_limit(self, date_filter):
        current_time = datetime.now()
        if date_filter == "Today":
            return current_time - timedelta(days=1)
        elif date_filter == "This Week":
            return current_time - timedelta(days=7)
        elif date_filter == "This Month":
            return current_time - timedelta(days=30)
        elif date_filter == "This Year":
            return current_time - timedelta(days=365)
        else:
            return None

    # def create_search_treeview(self):
    #     results_frame = ttk.Frame(self.search_results_window)
    #     results_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    #     self.results_count_label = ttk.Label(results_frame, text="Results: 0 items found")
    #     self.results_count_label.pack(anchor=tk.W, pady=(0, 5))

    #     self.search_tree = ttk.Treeview(results_frame)
    #     self.search_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    #     vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.search_tree.yview)
    #     vsb.pack(side=tk.RIGHT, fill=tk.Y)
    #     self.search_tree.configure(yscrollcommand=vsb.set)

    #     self.search_tree["columns"] = ("name", "path", "type", "size", "modified")
    #     self.search_tree.column("#0", width=40, minwidth=40)
    #     self.search_tree.column("name", width=200, minwidth=100)

    def create_widgets(self):
        style = ttk.Style()
        try:
            style.theme_use('vista' if os.name == 'nt' else 'clam')
        except tk.TclError:
            style.theme_use('default')
        
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        nav_frame = ttk.Frame(top_frame)
        nav_frame.pack(side=tk.LEFT)
        
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
            Tooltip(btn, tooltip_text)
        
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
        cloud_setup_btn = ttk.Button(cloud_frame, text="💭 Setup",
                                     command=self.setup_cloud_config)
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
        self.settings_button = ttk.Button(right_section, text="⚙️ Settings", 
                                        command=self.show_settings_dialog)
        self.settings_button.pack(side=tk.RIGHT, padx=2)
        
        
        
        # Automation window button
        self.automation_button = ttk.Button(right_section, text="⚙️ Automation",
                                            command=self.open_automation_window)
        self.automation_button.pack(side=tk.RIGHT, padx=2)
        
        # User Log View Button
        self.log_button = ttk.Button(right_section, text="Activity Log", command=self.show_activity_log)
        self.log_button.pack(side=tk.RIGHT, padx=2)
        
        # Cloud search button
        cloud_search_btn = ttk.Button(right_section, text="💭 Search",
                                      command=self.search_cloud_files)
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
        self.file_tree.bind("<Button-1>", self.deselect_on_empty_space, add="+")
################SETTING and DELETE ACCOUNT############################

    def show_settings_dialog(self):
        """Open a dialog with user settings including account deletion option"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("DocuVault Settings")
        settings_window.geometry("450x350")
        # Create main container with padding
        settings_frame = ttk.Frame(settings_window, padding=15)
        settings_frame.pack(fill="both", expand=True)
        ttk.Label(settings_window, text="Settings", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(settings_window, text="Add your settings options here").pack(pady=5)
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
        archive_section = ttk.LabelFrame(settings_frame, text="Archive Settings")
        archive_section.pack(fill="x", pady=10, padx=5)
        
        archive_toggle = ttk.Checkbutton(archive_section, text="Enable Auto-Archiving",
                                        variable=self.archive_mode,
                                        command=self.toggle_archive_options)
        archive_toggle.pack(pady=5)

        # Archive age selection
        self.age_frame = ttk.Frame(archive_section)
        self.age_frame.pack(pady=5)
        ttk.Label(self.age_frame, text="Archive files older than:").pack(side=tk.LEFT)
        age_entry = ttk.Entry(self.age_frame, textvariable=self.archive_age, width=5)
        age_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.age_frame, text="days").pack(side=tk.LEFT)

        # Initially disable age selection if archive mode is off
        self.toggle_archive_options()
        # Add Dashboard section
        dashboard_section = ttk.LabelFrame(settings_frame, text="Dashboard")
        dashboard_section.pack(fill="x", pady=10, padx=5)
        # Dashboard button
        dashboard_button = ttk.Button(dashboard_section, text="Open Dashboard", command=self.show_dashboard)
        dashboard_button.pack(pady=5)
        #Log Viewer
        log_section = ttk.LabelFrame(settings_frame, text="Activity Logs")
        log_section.pack(fill="x", pady=10, padx=5)
        #Log Button
        log_button = ttk.Button(log_section, text="View Logs", command=self.show_activity_log)
        log_button.pack(pady=5)
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

        elif self.current_dir == self.archive_dir:
            operations = [
                ("Delete", self.delete_item),
                ("Move", self.move_item),
                ("🗑 Empty Archive", self.empty_archive)

            ]

        else:
            operations = [
                ("Move", self.move_item),
                ("Copy", self.copy_item),
                ("Delete", self.delete_item),

                ("🗑 Open Bin", self.go_to_bin),
                ("📦Open Archive", self.go_to_archive)
            ]
        
        for text, command in operations:
            btn = ttk.Button(self.center_section, text=text, command=command)
            btn.pack(side=tk.LEFT, padx=2)

    def select_all(self, event=None):
        for item in self.file_tree.get_children():
            self.file_tree.selection_add(item)
        return "break"

    def go_to_root(self):
        if self.current_dir == self.bin_dir:
            restrict_access(self.bin_dir)
        self.current_dir = os.path.expanduser('~')
        self.update_file_list()

    def go_to_desktop(self):
        if self.current_dir == self.bin_dir:
            restrict_access(self.bin_dir)
        desktop_path = os.path.join(os.path.expanduser('~'), r'OneDrive\Desktop')
        if os.path.exists(desktop_path):
            self.current_dir = desktop_path
            self.update_file_list()
        else:
            messagebox.showinfo("Info", "Desktop directory not found.")

    

    def on_search_double_click(self, event):
        item_id = self.search_tree.selection()[0]
        item_values = self.search_tree.item(item_id, 'values')
        if item_values:
            item_path = item_values[0]
            if os.path.isfile(item_path):
                self.file_manager.open_file(item_path)
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
                self.file_manager.open_file(item_path)
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
                if (os.path.basename(self.bin_dir) in os.path.normpath(self.current_dir).split(os.path.sep)):
                    context_menu.add_command(label="Restore", command=lambda: self.restore_item())
                    context_menu.add_command(label="Delete", command=lambda: self.delete_item())
                    context_menu.add_command(label="Empty Bin", command=lambda: self.empty_bin())
                    context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                else:
                    context_menu.add_command(label="Open", command=lambda: self.open_file(item_path))
                    context_menu.add_command(label="Open With", command=lambda: self.open_with(item_path))
                    context_menu.add_command(label="Rename", command=lambda: self.rename_item(item_path))
                    context_menu.add_command(label="Copy", command=lambda: self.copy_item())
                    context_menu.add_command(label="Move", command=lambda: self.move_item())
                    context_menu.add_command(label="Delete", command=lambda: self.delete_item())
                    context_menu.add_command(label="Archive",command=lambda: self.archive_old_files())
                    context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(item_path))
                    context_menu.add_command(label="Upload to Cloud", 
                                            command=lambda: self.upload_to_cloud(item_path))
                
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

    def deselect_on_empty_space(self, event):
        """Deselect all items when clicking on empty space"""
        # Get the item (row) that was clicked
        item = self.file_tree.identify_row(event.y)       
        # If not clicking on a row (empty space), clear selection
        if not item:
            self.file_tree.selection_set([])  # Alternative way to clear
            self.file_tree.focus("")  # Clear focus as well
            return "break"

    def go_into_directory(self, path):
        if os.path.isdir(path):
            try:
                # Attempt to list the contents of the directory
                os.listdir(path)
                # If successful, update current_dir and file list
                self.current_dir = path
                self.update_file_list()
            except PermissionError:
                messagebox.showwarning("Access Denied", f"Permission denied for directory:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not access directory: {str(e)}")

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
        allow_access(self.bin_dir)
        self.current_dir = self.bin_dir
        self.update_file_list()

    def copy_path(self, item_path):
        """Copy file/folder path to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(item_path)

    def create_file(self):
        filename = simpledialog.askstring("Create File", "Enter file name:")
        success, message = self.file_manager.create_file(self.current_dir, filename)
        if success:
            self.update_file_list()
        else:
            messagebox.showerror("Error", message)

    def create_folder(self):
        foldername = simpledialog.askstring("Create Folder", "Enter folder name:")
        success, message = self.file_manager.create_folder(self.current_dir, foldername)
        if success:
            self.update_file_list()
        else:
            messagebox.showerror("Error", message)

    def rename_item(self, item_path):
        old_name = os.path.basename(item_path)
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=old_name)
        if new_name and new_name != old_name:
            success, message = self.file_manager.rename_item(item_path, new_name)
            if success:
                self.update_file_list()
            else:
                messagebox.showerror("Error", message)

    def delete_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_delete = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        if (os.path.basename(self.bin_dir) in os.path.normpath(self.current_dir).split(os.path.sep)):
            confirm = messagebox.askyesno("Confirm Permanent Deletion", "Are you sure you want to permanently delete the selected items?")
            if confirm:
                result = self.file_manager.delete_item(self.current_dir, items_to_delete, permanently=True)
            else:
                return
        else:
            response = messagebox.askyesnocancel("Delete Items",
                f"What would you like to do with the selected item(s)?\n\nYes = Delete permanently\nNo = Move to Bin\nCancel = Abort operation")
            if response is None:  # Cancel
                return
            if response:
                result = self.file_manager.delete_item(self.current_dir, items_to_delete, permanently=True)
            else:
                result = self.file_manager.delete_item(self.current_dir, items_to_delete)
        
        if result["success_count"] > 0:
            messagebox.showinfo("Success", f"Successfully deleted {result['success_count']} item(s)")
        
        if result["failed_items"]:
            failed_msg = "\n".join(result["failed_items"])
            messagebox.showerror("Error", f"Failed to delete some items:\n{failed_msg}")
        
        if result["skipped_items"]:
            skipped_msg = "\n".join(result["skipped_items"])
            messagebox.showinfo("Info", f"Skipped items:\n{skipped_msg}")
        self.update_file_list()

    def move_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_move = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)  # Wait for dialog to close
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.move_item(items_to_move, destination)
            if result["success_count"] > 0:
                messagebox.showinfo("Success", f"Successfully moved {result['success_count']} item(s) to {result['destination']}")
            
            if result["failed_items"]:
                failed_msg = "\n".join(result["failed_items"])
                messagebox.showerror("Error", f"Failed to move some items:\n{failed_msg}")
            
            if result["skipped_items"]:
                skipped_msg = "\n".join(result["skipped_items"])
                messagebox.showinfo("Info", f"Skipped items:\n{skipped_msg}")
        self.update_file_list()
    
    def copy_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_copy = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)  # Wait for dialog to close
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.copy_item(items_to_copy, destination)
            if result["success_count"] > 0:
                messagebox.showinfo("Success", f"Successfully copied {result['success_count']} item(s) to {result['destination']}")
            
            if result["failed_items"]:
                failed_msg = "\n".join(result["failed_items"])
                messagebox.showerror("Error", f"Failed to copy some items:\n{failed_msg}")
        self.update_file_list()

    def empty_bin(self):
        confirm = messagebox.askyesno("Confirm Empty Bin", "Are you sure you want to permanently delete all items in the Bin?")
        if confirm:
            result = self.file_manager.empty_bin()
            if isinstance(result, dict):
                if result["success_count"] > 0:
                    messagebox.showinfo("Success", f"Successfully deleted {result['success_count']} item(s) from the Bin")
                if result["failed_items"]:
                    failed_msg = "\n".join(result["failed_items"])
                    messagebox.showerror("Error", f"Failed to delete some items:\n{failed_msg}")
            else:
                messagebox.showinfo("Info", result)
        self.update_file_list()

    def restore_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return
        
        items_to_restore = [self.file_tree.item(item, 'values')[1] for item in selected_items]
        
        dest_dialog = CustomDirectoryDialog(self.root, self.current_dir)
        self.root.wait_window(dest_dialog)
        
        destination = dest_dialog.selected_path
        if destination:
            result = self.file_manager.restore_item(items_to_restore, destination)
            if result["success_count"] > 0:
                messagebox.showinfo("Success", f"Successfully restored {result['success_count']} item(s) to {result['destination']}")
            
            if result["failed_items"]:
                failed_msg = "\n".join(result["failed_items"])
                messagebox.showerror("Error", f"Failed to restore some items:\n{failed_msg}")
        self.update_file_list()

    def open_file(self, item_path):
        if os.path.isfile(item_path):
            success, message = self.file_manager.open_file(item_path)
            if not success:
                messagebox.showerror("Error", message)
        elif os.path.isdir(item_path):
            self.go_into_directory(item_path)
        else:
            messagebox.showinfo("Info", "Selected item cannot be opened")

    def open_with(self, item_path):
        available_apps = self.file_manager.get_available_apps(item_path)
        if not available_apps:
            messagebox.showinfo("Info", "No applications found to open this file")
            return
        
        app_window = tk.Toplevel(self.root)
        app_window.title("Open With")
        app_window.geometry("400x300")
        
        listbox = tk.Listbox(app_window)
        listbox.pack(expand=True, fill=tk.BOTH)
        
        for app in available_apps:
            listbox.insert(tk.END, app[0])
        
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
                
                app_window.destroy()
        
        listbox.bind('<Double-1>', on_double_click)

    def show_activity_log(self):
        LogViewer(self.root, self.username)
    def sign_out(self, time_out = False):
        if not time_out:
            """Handle sign out process"""
            confirm = messagebox.askyesno("Confirm Sign Out", 
                "Are you sure you want to sign out?")
            
            if confirm:
                self.root.destroy()
                from login import LoginPage
                login_page = LoginPage()
                login_page.mainloop()
        else:
            if hasattr(self, 'activity_timer_id') and self.activity_timer_id:
                self.root.after_cancel(self.activity_timer_id)
            
            # Close the current window
            self.root.destroy()
            
            # Start the login page
            from login import LoginPage
            login_page = LoginPage()
            login_page.mainloop()
    ##############################
    # Automation Callbacks       #
    ##############################
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

    ##############################
    # Cloud Operations Callbacks #
    ##############################
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

    def setup_cloud_config(self):
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
            ttk.Label(config_win, text=label).pack()
            entry = ttk.Entry(config_win)
            entry.pack(pady=5)
            entry_widgets[field_name] = entry
        
        def save_config():
            url=entry_widgets["server_url"].get()
            user=entry_widgets["cloud_user"].get()
            password=entry_widgets["cloud_pass"].get()

            if not url or not user or not password:
                messagebox.showerror("Error", "Please fill in all fields")
                return
            self.cloud.store_credentials(
                server_url=url,
                cloud_user=user,
                cloud_pass=password,
                master_password=self.get_master_password()
            )
            config_win.destroy()
        
        ttk.Button(config_win, text="Save", command=save_config).pack(pady=10)

    def get_master_password(self):
        return simpledialog.askstring("Security Check",
                                      "Enter your master password for auto-connecting to cloud:",
                                      show='*')
    def show_progress(self, message):
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
        if message:
            self.progress_label.config(text=message)
        self.progress_bar['value'] = value
        if value >= 100 and message:
            if "Connected to Nextcloud" in message:
                self.update_cloud_status('connected')
            self.progress_window.after(2000, self.progress_window.destroy)

    def delete_cloud_item(self, cloud_path):
        remote_path = f"/DocuVault/{os.path.basename(cloud_path)}"
        if messagebox.askyesno("Confirm", "Delete from cloud?"):
            self.cloud.delete_file(remote_path)

    def show_error(self, message):
        messagebox.showerror("Cloud Error", message)
        if "Connection failed" in message:
            self.update_cloud_status('failed')
        if hasattr(self, 'progress_window') and self.progress_window and tk.Toplevel.winfo_exists(self.progress_window):
            self.progress_window.destroy()

    def show_info(self, message):
        messagebox.showinfo("Cloud Info", message)

    def display_cloud_results(self, results):
        if self.search_results_window and tk.Toplevel.winfo_exists(self.search_results_window):
            self.search_tree.tag_configure(tagname='cloud', foreground='blue')
            if not results or len(results) == 0:
                self.search_tree.insert("", "end",
                                        text="No matching cloud records",
                                        values=("",),
                                        tags=('cloud',))
                return
            for item in results:
                self.search_tree.insert("", "end",
                                        text=item.name,
                                        values=(f"Cloud: {item.user_path}",),
                                        tags=('cloud',))

    def search_cloud_files(self):
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
            if os.path.exists(local_path):
                overwrite = messagebox.askyesno(
                    "File Already Exists",
                    f"The file '{filename}' already exists in the destination folder.\n\nDo you want to overwrite it?"
                )
                if not overwrite:
                    rename = messagebox.askyesno(
                        "Rename File",
                        "Do you want to rename the downloading file?"
                    )
                    if rename:
                        new_name = simpledialog.askstring(
                            "Rename File",
                            "Enter a new name for the file:"
                        )
                        if not new_name:
                            messagebox.showinfo("Info", "Download canceled")
                            return
                        file_ext = os.path.splitext(filename)[1]
                        if not new_name.endswith(file_ext):
                            new_name += file_ext
                        new_path = os.path.join(dest_dir, new_name)
                        if os.path.exists(new_path):
                            messagebox.showerror("Error", f"A file named '{new_name}' also exists. Download aborted.")
                            return
                        self.cloud.download_file(
                            remote_path=remote_path,
                            local_dir=dest_dir,
                            custom_local_path=new_path
                        )
                        return
                    else:
                        messagebox.showinfo("Info", "Download canceled")
                        return
            self.cloud.download_file(
                remote_path=remote_path,
                local_dir=dest_dir
            )

    def upload_to_cloud(self, local_path):
        if os.path.isdir(local_path):
            messagebox.showinfo("Cloud Upload", "Folder can't be uploaded. Please select a file.")
            return
        if self.cloud and self.cloud.nc:
            self.cloud.upload_file(local_path, f"/DocuVault/{os.path.basename(local_path)}")
        else:
            messagebox.showinfo("Cloud Upload", "Please connect to cloud first")

    def run(self):
        self.root.mainloop()
