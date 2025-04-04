import tkinter as tk
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk
from datetime import datetime
import numpy as np
from PIL import Image, ImageTk
from tkinter import messagebox
from utility import CustomDirectoryDialog

class Dashboard:
    def __init__(self, parent, first_time=True):
        # Configure customtkinter appearance
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.parent = parent
        self.first_time = first_time
        self.callback_ids = [] # Track scheduled callbacks
        
        # Create more compact window
        self.dashboard_window = ctk.CTkToplevel(parent.root)
        self.dashboard_window.title("DocuVault Dashboard")

        # # Add escape key binding to exit fullscreen mode
        self.dashboard_window.bind('<Escape>', lambda event: self.toggle_fullscreen())

        # Tell window to start maximized
        if os.name == 'nt':
            self.dashboard_window.state('zoomed')  # Windows
        else:
            self.dashboard_window.attributes('-zoomed', True)

        # After creating the dashboard_window
        self.dashboard_window.focus_force()
        self.dashboard_window.lift()
        self.dashboard_window.attributes('-topmost', True)
        self.dashboard_window.attributes('-topmost', False)
        self.dashboard_window.grab_set()

        
        # Configure grid layout - more compact
        self.dashboard_window.grid_columnconfigure(0, weight=1)
        self.dashboard_window.grid_columnconfigure(1, weight=1)
        self.dashboard_window.grid_rowconfigure(0, weight=0) # Header row
        self.dashboard_window.grid_rowconfigure(1, weight=1) # Main content row
        self.dashboard_window.grid_rowconfigure(2, weight=0) # Bottom row
        
        self.dashboard_window.protocol("WM_DELETE_WINDOW", self.on_close)
        # Try to set icon
        try:
            self.dashboard_window.iconbitmap("AppIcon\\DocuVault-icon.ico")
        except Exception:
            pass
            
        # Create compact header with user info and time
        self.create_compact_header()
        
        # Create left panel with stats and navigation
        self.create_left_panel()
        
        # Create right panel with chart and storage
        self.create_right_panel()
        
        # Schedule updates
        update_id = self.dashboard_window.after(1000, self.update_time)
        self.callback_ids.append(update_id)
    
    def toggle_fullscreen(self):
        """Toggle between fullscreen and normal window mode"""
        if self.dashboard_window.attributes('-fullscreen'):
            self.dashboard_window.attributes('-fullscreen', False)
        else:
            self.dashboard_window.attributes('-fullscreen', True)
    
    def update_time(self):
        """Update time display"""
        if hasattr(self, 'time_label') and self.time_label.winfo_exists():
            current_time = datetime.now().strftime("%H:%M:%S")
            self.time_label.configure(text=current_time)
            
        # Schedule next update
        if hasattr(self, 'dashboard_window') and self.dashboard_window.winfo_exists():
            update_id = self.dashboard_window.after(1000, self.update_time)
            self.callback_ids.append(update_id)
    
    def create_compact_header(self):
        """Create compact header with welcome and time"""
        header_frame = ctk.CTkFrame(self.dashboard_window)
        header_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Welcome text and current time side by side
        welcome_text = f"Hello, {self.parent.username}"
        welcome_label = ctk.CTkLabel(
            header_frame,
            text=welcome_text,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        welcome_label.pack(side="left", padx=10)
        
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label = ctk.CTkLabel(
            header_frame,
            text=current_time,
            font=ctk.CTkFont(size=14)
        )
        self.time_label.pack(side="right", padx=10)
    
    def create_left_panel(self):
        """Create left panel with file stats and navigation"""
        left_panel = ctk.CTkFrame(self.dashboard_window)
        left_panel.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Configure grid for left panel
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(0, weight=1) # Stats section
        left_panel.grid_rowconfigure(1, weight=1) # Navigation section
        
        # Create more compact stats section
        self.create_compact_stats(left_panel)
        
        # Create more compact navigation section
        self.create_compact_navigation(left_panel)
    
    def create_compact_stats(self, parent):
        """Create compact statistics display"""
        stats_frame = ctk.CTkFrame(parent)
        stats_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Add title
        title = ctk.CTkLabel(
            stats_frame,
            text="File Statistics",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(5, 10))
        
        # Get file counts
        home_dir = os.path.join(os.path.expanduser("~"), r"OneDrive\Desktop")
        text_count, image_count, video_count = self.parent.count_files_by_type(home_dir)
        total_count = max(1, text_count + image_count + video_count)
        
        # Create more compact stat display
        stat_container = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stat_container.pack(fill="both", expand=True, padx=5)
        
        # Configure grid for stat items
        stat_container.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Create smaller stat items
        self.create_stat_item(stat_container, 0, "Text", text_count, total_count, "#5DA7DB")
        self.create_stat_item(stat_container, 1, "Image", image_count, total_count, "#7077A1")
        self.create_stat_item(stat_container, 2, "Video", video_count, total_count, "#F6AE99")
    
    def create_stat_item(self, parent, column, title, count, total, color):
        """Create smaller stat display item"""
        item = ctk.CTkFrame(parent, fg_color=color, corner_radius=6)
        item.grid(row=0, column=column, padx=3, pady=3, sticky="nsew")
        
        # Title
        title_label = ctk.CTkLabel(
            item,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        title_label.pack(pady=(5, 0))
        
        # Count
        count_label = ctk.CTkLabel(
            item,
            text=str(count),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        count_label.pack(pady=0)
        
        # Percentage
        percentage = (count / total) * 100
        percentage_label = ctk.CTkLabel(
            item,
            text=f"{percentage:.1f}%",
            font=ctk.CTkFont(size=10),
            text_color="white"
        )
        percentage_label.pack(pady=(0, 5))
    
    def create_compact_navigation(self, parent):
        """Create compact navigation section"""
        nav_frame = ctk.CTkFrame(parent)
        nav_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Title
        title = ctk.CTkLabel(
            nav_frame,
            text="Quick Navigation",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(5, 10))
        
        # Button container
        button_container = ctk.CTkFrame(nav_frame, fg_color="transparent")
        button_container.pack(fill="both", expand=True, padx=5, pady=5)
        button_container.columnconfigure((0, 1), weight=1)
        
        # Create smaller buttons in a 2x2 grid
        home_btn = ctk.CTkButton(
            button_container,
            text="Home",
            command=lambda: self.go_to_directory(os.path.expanduser("~")),
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            height=30
        )
        home_btn.grid(row=0, column=0, padx=3, pady=3, sticky="ew")
        
        desktop_btn = ctk.CTkButton(
            button_container,
            text="Desktop",
            command=lambda: self.go_to_directory(
                os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
            ),
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            height=30
        )
        desktop_btn.grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        
        current_btn = ctk.CTkButton(
            button_container,
            text="Current Dir",
            command=lambda: self.go_to_directory(os.getcwd()),
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            height=30
        )
        current_btn.grid(row=1, column=0, padx=3, pady=3, sticky="ew")
        
        return_btn = ctk.CTkButton(
            button_container,
            text="Back to Files",
            command=self.select_directory,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            height=30
        )
        return_btn.grid(row=1, column=1, padx=3, pady=3, sticky="ew")

    def select_directory(self):
        """Select directory to navigate to"""
        directory = CustomDirectoryDialog(self.parent.root, self.parent.current_dir)
        self.parent.root.wait_window(directory)
        if directory.selected_path:
            self.go_to_directory(directory.selected_path)

    def create_right_panel(self):
        """Create right panel with chart and storage info"""
        right_panel = ctk.CTkFrame(self.dashboard_window)
        right_panel.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        
        # Configure grid for right panel
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=2) # Chart section (larger)
        right_panel.grid_rowconfigure(1, weight=1) # Storage section
        
        # Create more compact chart
        self.create_compact_chart(right_panel)
        
        # Create more compact storage display
        self.create_compact_storage(right_panel)
    
    def create_compact_chart(self, parent):
        """Create more compact file type chart"""
        chart_frame = ctk.CTkFrame(parent)
        chart_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Title
        title = ctk.CTkLabel(
            chart_frame,
            text="File Type Distribution",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(5, 5))
        
        # Get file type data
        file_types = self.get_file_type_distribution()
        
        # Filter out small values
        threshold = 0.03 # 3%
        other_sum = 0
        filtered_types = {}
        total = sum(file_types.values())
        
        if total == 0:
            filtered_types = {".empty": 1}
        else:
            for ext, count in file_types.items():
                percentage = count / total
                if percentage >= threshold:
                    filtered_types[ext] = count
                else:
                    other_sum += count
                    
        # Add "Other" category if needed
        if other_sum > 0:
            filtered_types["Other"] = other_sum
        
        # Create smaller figure
        fig, ax = plt.subplots(figsize=(3.5, 3), dpi=100)
        fig.patch.set_facecolor('none')
        ax.set_facecolor('none')
        
        # Create compact pie chart
        wedges, _, autotexts = ax.pie(
            filtered_types.values(),
            labels=None,
            autopct='%1.1f%%',
            startangle=90,
            shadow=False,
            colors=plt.cm.tab10.colors[:len(filtered_types)],
            wedgeprops={'width': 0.5, 'edgecolor': 'white', 'linewidth': 1},
            textprops={'fontsize': 8, 'fontweight': 'bold'}
        )
        
        # Set equal aspect ratio
        ax.axis('equal')
        
        # Add smaller legend
        ax.legend(
            wedges,
            filtered_types.keys(),
            title="File Types",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=7
        )
        
        # Create canvas widget
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
    
    def create_compact_storage(self, parent):
        """Create compact storage display"""
        storage_frame = ctk.CTkFrame(parent)
        storage_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Title
        title = ctk.CTkLabel(
            storage_frame,
            text="Storage Usage",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(5, 5))
        
        # Get disk usage stats
        try:
            total, used, free = self.get_disk_usage(os.path.expanduser("~"))
            percentage_used = (used / total) * 100
        except Exception:
            # Fallback values
            total = 100
            used = 50
            free = 50
            percentage_used = 50
        
        # Choose color based on percentage
        if percentage_used < 70:
            progress_color = "#4CAF50" # Green
        elif percentage_used < 90:
            progress_color = "#FF9800" # Orange
        else:
            progress_color = "#F44336" # Red
        
        # Create progress bar
        progress_bar = ctk.CTkProgressBar(storage_frame, width=250, height=15)
        progress_bar.set(percentage_used/100)

        progress_bar.configure(progress_color=progress_color)
        progress_bar.pack(pady=10)
        
        # Percentage and size labels
        info_text = f"{percentage_used:.1f}% Used • {self.format_size(used)} of {self.format_size(total)}"
        info_label = ctk.CTkLabel(
            storage_frame,
            text=info_text,
            font=ctk.CTkFont(size=12)
        )
        info_label.pack(pady=0)
    
    def get_file_type_distribution(self):
        """Get distribution of file types (limited scan)"""
        file_types = {}
        max_files = 500  # Limit files scanned for performance
        file_count = 0
        
        for root, _, files in os.walk(os.path.expanduser("~"), topdown=True):
            # Skip system directories
            if any(skip_dir in root for skip_dir in ['.git', 'node_modules', '__pycache__']):
                continue
                
            try:
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if not ext:
                        continue
                    file_types[ext] = file_types.get(ext, 0) + 1
                    
                    file_count += 1
                    if file_count >= max_files:
                        return file_types
            except:
                continue
                
        return file_types
    
    def get_disk_usage(self, path):
        """Get disk usage statistics"""
        if os.name == 'posix':
            # Unix/Linux/MacOS
            import shutil
            total, used, free = shutil.disk_usage(path)
        else:
            # Windows
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(path), None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes)
            )
            total = total_bytes.value
            free = free_bytes.value
            used = total - free
            
        return total, used, free
    
    def format_size(self, size_bytes):
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    def go_to_directory(self, path):
        """Navigate to the specified directory in the main file manager"""
        if os.path.exists(path):
            # Cancel all scheduled callbacks
            for callback_id in self.callback_ids:
                try:
                    self.dashboard_window.after_cancel(callback_id)
                except:
                    pass
                    
            # Close any matplotlib figures
            plt.close('all')
            
            self.parent.initialize_main_window(path)
            self.dashboard_window.destroy()
        else:
            messagebox.showinfo("Directory Not Found", f"The directory {path} does not exist.")


    def on_close(self):
        for callback_id in self.callback_ids:
            try:
                self.dashboard_window.after_cancel(callback_id)
            except:
                pass
        # Close any matplotlib figures
        plt.close('all')
        if self.first_time:
            try:
                self.parent.root.quit()
                self.parent.root.destroy()
            except:
                pass
            finally:
                return
        else:
            self.parent.initialize_main_window(self.parent.current_dir)
            # Ensure main window has focus
            self.parent.root.focus_force()
        # Destroy the dashboard window
        self.dashboard_window.destroy()
