# =====================================================================================================================================
# Old dashboard
# ======================================================================================================================================

# import tkinter as tk
# import os
# import matplotlib.pyplot as plt
# import plotly.express as px
# import plotly.graph_objects as go
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import customtkinter as ctk
# from datetime import datetime
# import numpy as np
# from PIL import Image, ImageTk
# from tkinter import messagebox

# class Dashboard:
#     def __init__(self, parent):
#         # Configure customtkinter appearance
#         ctk.set_appearance_mode("System")  # Modes: "System", "Dark", "Light"
#         ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"
        
#         self.parent = parent
#         self.callback_ids = []  # Track scheduled callbacks
#         # Create modern window
#         self.dashboard_window = ctk.CTkToplevel(parent.root)
#         self.dashboard_window.title("DocuVault Dashboard")
#         self.dashboard_window.geometry("1000x700")
#         self.dashboard_window.grid_columnconfigure(0, weight=1)
#         self.dashboard_window.grid_rowconfigure(0, weight=1)
        
#         # Try to set icon
#         try:
#             self.dashboard_window.iconbitmap("AppIcon\\DocuVault-icon.ico")
#         except Exception as e:
#             print(f"Error setting icon: {e}")
        
#         # Create main frame
#         self.main_frame = ctk.CTkFrame(self.dashboard_window)
#         self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
#         self.main_frame.grid_columnconfigure(0, weight=1)
#         self.main_frame.grid_columnconfigure(1, weight=1)
        
#         # Create dashboard sections
#         self.create_header_section()
#         self.create_stats_section()
#         self.create_navigation_section()
#         self.create_charts_section()
#         self.create_storage_section()

#     def update_something(self):
#         """Update dynamic dashboard elements"""
#         # Example: Update current time
#         current_time = datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
#         if hasattr(self, 'time_label') and self.time_label.winfo_exists():
#             self.time_label.configure(text=current_time)
        
#         # Schedule next update
#         if hasattr(self, 'dashboard_window') and self.dashboard_window.winfo_exists():
#             update_id = self.dashboard_window.after(1000, self.update_something)
#             self.callback_ids.append(update_id)


#     def create_header_section(self):
#         """Create header with welcome message and time"""
#         header_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
#         header_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
#         header_frame.grid_columnconfigure(0, weight=1)
        
#         # Welcome message
#         welcome_text = f"Hello, {self.parent.username}!"
#         welcome_label = ctk.CTkLabel(
#             header_frame, 
#             text=welcome_text, 
#             font=ctk.CTkFont(size=24, weight="bold")
#         )
#         welcome_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
#         # Subtitle
#         subtitle = ctk.CTkLabel(
#             header_frame, 
#             text="Welcome to your DocuVault Dashboard", 
#             font=ctk.CTkFont(size=16)
#         )
#         subtitle.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
#         # Current date/time
#         current_time = datetime.now().strftime("%A, %B %d, %Y %H:%M")
#         time_label = ctk.CTkLabel(
#             header_frame, 
#             text=current_time, 
#             font=ctk.CTkFont(size=14)
#         )
#         time_label.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="e")

#         # Start the update cycle
#         update_id = self.dashboard_window.after(1000, self.update_something)
#         self.callback_ids.append(update_id)

#     def create_stats_section(self):
#         """Create file statistics section with cards"""
#         stats_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
#         stats_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
#         stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
#         # Get file counts
#         text_count, image_count, video_count = self.parent.count_files_by_type(os.path.expanduser("~"))
#         total_count = max(1, text_count + image_count + video_count)  # Avoid division by zero
        
#         # Create colorful stat cards
#         self.create_stat_card(stats_frame, 0, "Text Files", text_count, total_count, "#5DA7DB")
#         self.create_stat_card(stats_frame, 1, "Image Files", image_count, total_count, "#7077A1")
#         self.create_stat_card(stats_frame, 2, "Video Files", video_count, total_count, "#F6AE99")
        
#     def create_stat_card(self, parent, column, title, count, total, accent_color):
#         """Create an individual statistic card"""
#         card = ctk.CTkFrame(parent, corner_radius=6, fg_color=accent_color)
#         card.grid(row=0, column=column, padx=10, pady=10, sticky="nsew")
        
#         # Title
#         title_label = ctk.CTkLabel(
#             card, 
#             text=title, 
#             font=ctk.CTkFont(size=16, weight="bold"),
#             text_color="white"
#         )
#         title_label.pack(pady=(15, 5))
        
#         # Count
#         count_label = ctk.CTkLabel(
#             card, 
#             text=str(count), 
#             font=ctk.CTkFont(size=28, weight="bold"),
#             text_color="white"
#         )
#         count_label.pack(pady=5)
        
#         # Percentage
#         percentage = (count / total) * 100
#         percentage_label = ctk.CTkLabel(
#             card, 
#             text=f"{percentage:.1f}%", 
#             font=ctk.CTkFont(size=14),
#             text_color="white"
#         )
#         percentage_label.pack(pady=(5, 15))

#     def create_navigation_section(self):
#         """Create quick navigation buttons"""
#         nav_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
#         nav_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
#         nav_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
#         # Section title
#         title = ctk.CTkLabel(
#             nav_frame, 
#             text="Quick Navigation", 
#             font=ctk.CTkFont(size=16, weight="bold")
#         )
#         title.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")
        
#         # Navigation buttons
#         home_btn = ctk.CTkButton(
#             nav_frame, 
#             text="Home", 
#             command=lambda: self.go_to_directory(os.path.expanduser("~")),
#             font=ctk.CTkFont(size=14),
#             corner_radius=8,
#             height=40
#         )
#         home_btn.grid(row=1, column=0, padx=10, pady=(10, 20), sticky="ew")
        
#         desktop_btn = ctk.CTkButton(
#             nav_frame, 
#             text="Desktop", 
#             command=lambda: self.go_to_directory(
#                 r"C:\Users\shara\OneDrive\Attachments\Desktop" 
#                 if os.path.exists(r"C:\Users\shara\OneDrive\Attachments\Desktop") 
#                 else os.path.join(os.path.expanduser("~"), "Desktop")
#             ),
#             font=ctk.CTkFont(size=14),
#             corner_radius=8,
#             height=40
#         )
#         desktop_btn.grid(row=1, column=1, padx=10, pady=(10, 20), sticky="ew")
        
#         cwd_btn = ctk.CTkButton(
#             nav_frame, 
#             text="Current Directory", 
#             command=lambda: self.go_to_directory(os.getcwd()),
#             font=ctk.CTkFont(size=14),
#             corner_radius=8,
#             height=40
#         )
#         cwd_btn.grid(row=1, column=2, padx=10, pady=(10, 20), sticky="ew")

#     def create_charts_section(self):
#         """Create file distribution chart section"""
#         charts_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
#         charts_frame.grid(row=1, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
#         charts_frame.grid_columnconfigure(0, weight=1)
#         charts_frame.grid_rowconfigure(1, weight=1)
        
#         # Section title
#         title = ctk.CTkLabel(
#             charts_frame, 
#             text="File Type Distribution", 
#             font=ctk.CTkFont(size=16, weight="bold")
#         )
#         title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
#         # Chart container
#         chart_frame = ctk.CTkFrame(charts_frame, corner_radius=6, fg_color="transparent")
#         chart_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
#         # Create and embed the chart
#         self.create_file_type_chart(chart_frame)
        
#         # Button for detailed analysis
#         chart_btn = ctk.CTkButton(
#             charts_frame, 
#             text="Show Detailed Chart", 
#             command=self.show_file_type_chart,
#             font=ctk.CTkFont(size=14),
#             corner_radius=8,
#             height=40
#         )
#         chart_btn.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

#     def create_storage_section(self):
#         """Create storage usage visualization section"""
#         storage_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
#         storage_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
#         storage_frame.grid_columnconfigure(0, weight=1)
#         storage_frame.grid_rowconfigure(1, weight=1)  # Give weight to gauge row
        
#         # Section title
#         title = ctk.CTkLabel(
#             storage_frame, 
#             text="Storage Overview", 
#             font=ctk.CTkFont(size=16, weight="bold")
#         )
#         title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
#         # Storage gauge container with explicit minimum height
#         gauge_frame = ctk.CTkFrame(storage_frame, corner_radius=6, fg_color="transparent", height=150)
#         gauge_frame.grid(row=1, column=0, padx=10, pady=(0, 20), sticky="nsew")
#         gauge_frame.grid_propagate(False)  # Prevent frame from shrinking
        
#         # Create storage gauge visualization
#         self.create_storage_gauge(gauge_frame)

#     def create_file_type_chart(self, parent):
#         """Create a pie chart for file type distribution"""
#         # Get file type data
#         file_types = self.get_file_type_distribution()
        
#         # Filter out small values
#         threshold = 0.03  # 3%
#         other_sum = 0
#         filtered_types = {}
        
#         total = sum(file_types.values())
#         if total == 0:
#             # Handle empty data
#             filtered_types = {".empty": 1}
#         else:
#             for ext, count in file_types.items():
#                 percentage = count / total
#                 if percentage >= threshold:
#                     filtered_types[ext] = count
#                 else:
#                     other_sum += count
                    
#             # Add "Other" category if needed
#             if other_sum > 0:
#                 filtered_types["Other"] = other_sum
        
#         # Create figure with transparent background
#         fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
#         fig.patch.set_facecolor('none')
#         ax.set_facecolor('none')
        
#         # Create pie chart with modern styling
#         wedges, texts, autotexts = ax.pie(
#             filtered_types.values(),
#             labels=None,
#             autopct='%1.1f%%',
#             startangle=90,
#             shadow=False,
#             colors=plt.cm.tab10.colors[:len(filtered_types)],
#             wedgeprops={'width': 0.5, 'edgecolor': 'white', 'linewidth': 2},
#             textprops={'color': 'white', 'fontsize': 11, 'fontweight': 'bold'}
#         )
        
#         # Set equal aspect ratio
#         ax.axis('equal')
        
#         # Add a legend
#         ax.legend(
#             wedges,
#             filtered_types.keys(),
#             title="File Types",
#             loc="center left",
#             bbox_to_anchor=(0.9, 0, 0.5, 1)
#         )
        
#         # Create canvas widget
#         canvas = FigureCanvasTkAgg(fig, master=parent)
#         canvas.draw()
#         canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

#         update_id = self.dashboard_window.after(1000, self.update_something)
#         self.callback_ids.append(update_id)
    
#     def create_storage_gauge(self, parent):
#         """Create a gauge chart showing storage usage"""
#         # Get disk usage stats
#         try:
#             total, used, free = self.get_disk_usage(os.path.expanduser("~"))
#             percentage_used = (used / total) * 100
#         except Exception as e:
#             # Fallback values
#             total = 100
#             used = 50
#             free = 50
#             percentage_used = 50
        
#         try:
#             # Alternative approach with custom drawing instead of matplotlib
#             container = ctk.CTkFrame(parent, fg_color="transparent")
#             container.pack(fill="both", expand=True, padx=20, pady=20)
            
#             # Storage usage label
#             title_label = ctk.CTkLabel(
#                 container, 
#                 text="Storage Usage", 
#                 font=ctk.CTkFont(size=16, weight="bold")
#             )
#             title_label.pack(pady=(0, 10))
            
#             # Create progress bar
#             if percentage_used < 70:
#                 progress_color = "#4CAF50"  # Green
#             elif percentage_used < 90:
#                 progress_color = "#FF9800"  # Orange
#             else:
#                 progress_color = "#F44336"  # Red
                
#             progress_bar = ctk.CTkProgressBar(container, width=400, height=25)
#             progress_bar.set_value(percentage_used/100)
#             progress_bar.configure(progress_color=progress_color)
#             progress_bar.pack(pady=10)
            
#             # Percentage and size labels
#             percent_label = ctk.CTkLabel(
#                 container, 
#                 text=f"{percentage_used:.1f}% Used", 
#                 font=ctk.CTkFont(size=14)
#             )
#             percent_label.pack(pady=5)
            
#             size_label = ctk.CTkLabel(
#                 container, 
#                 text=f"{self.format_size(used)} of {self.format_size(total)}", 
#                 font=ctk.CTkFont(size=12)
#             )
#             size_label.pack()
            
#             # Store reference to prevent garbage collection
#             self.storage_progress = progress_bar
            
#         except Exception as e:
#             # Fallback text display if visualization fails
#             fallback_label = ctk.CTkLabel(
#                 parent,
#                 text=f"Storage: {percentage_used:.1f}% Used\n{self.format_size(used)} of {self.format_size(total)}",
#                 font=ctk.CTkFont(size=14)
#             )
#             fallback_label.pack(pady=40)

#     def get_file_type_distribution(self):
#         """Get distribution of file types"""
#         file_types = {}
        
#         for root, _, files in os.walk(os.path.expanduser("~"), topdown=True):
#             # Skip system directories
#             skip_dirs = ['.git', 'node_modules', '__pycache__', '.vscode', '.idea']
#             if any(skip_dir in root for skip_dir in skip_dirs):
#                 continue
                
#             try:
#                 for file in files[:1000]:  # Limit for performance
#                     ext = os.path.splitext(file)[1].lower()
#                     if not ext:  # Skip files with no extension
#                         continue
#                     file_types[ext] = file_types.get(ext, 0) + 1
#             except:
#                 continue
                
#         return file_types

#     def get_disk_usage(self, path):
#         """Get disk usage statistics"""
#         if os.name == 'posix':
#             # Unix/Linux/MacOS
#             import shutil
#             total, used, free = shutil.disk_usage(path)
#         else:
#             # Windows
#             import ctypes
#             free_bytes = ctypes.c_ulonglong(0)
#             total_bytes = ctypes.c_ulonglong(0)
#             ctypes.windll.kernel32.GetDiskFreeSpaceExW(
#                 ctypes.c_wchar_p(path), None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes)
#             )
#             total = total_bytes.value
#             free = free_bytes.value
#             used = total - free
            
#         return total, used, free

#     def format_size(self, size_bytes):
#         """Format bytes to human-readable size"""
#         for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
#             if size_bytes < 1024:
#                 return f"{size_bytes:.1f} {unit}"
#             size_bytes /= 1024
#         return f"{size_bytes:.1f} PB"

#     def show_file_type_chart(self):
#         """Show interactive file type chart using plotly"""
#         # Get file type data
#         file_types = self.get_file_type_distribution()
        
#         # Convert to lists for plotly
#         labels = list(file_types.keys())
#         values = list(file_types.values())
        
#         # Create a donut chart
#         fig = go.Figure(data=[go.Pie(
#             labels=labels,
#             values=values,
#             hole=.4,
#             textinfo='label+percent',
#             insidetextorientation='radial'
#         )])
        
#         # Update layout
#         fig.update_layout(
#             title_text='File Type Distribution',
#             font=dict(size=14),
#             paper_bgcolor='rgba(0,0,0,0)',
#             plot_bgcolor='rgba(0,0,0,0)'
#         )
        
#         # Show the interactive plot
#         fig.show()

#     def go_to_directory(self, path):
#         """Navigate to the specified directory in the main file manager"""
#         if os.path.exists(path):
#             # Cancel all scheduled callbacks to prevent errors
#             for callback_id in self.callback_ids:
#                 try:
#                     self.dashboard_window.after_cancel(callback_id)
#                 except:
#                     pass
            
#             # Close any matplotlib figures
#             plt.close('all')
            
#             self.parent.initialize_main_window(path)
#             self.dashboard_window.destroy()
#         else:
#             messagebox.showinfo("Directory Not Found", f"The directory {path} does not exist.")

# ====================================================================================================================
# new enhanced dashboard
# ====================================================================================================================

import tkinter as tk
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk
from datetime import datetime
import numpy as np
from PIL import Image, ImageTk
from tkinter import messagebox

class Dashboard:
    def __init__(self, parent):
        # Configure customtkinter appearance
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.parent = parent
        self.callback_ids = [] # Track scheduled callbacks
        
        # Create more compact window
        self.dashboard_window = ctk.CTkToplevel(parent.root)
        self.dashboard_window.title("DocuVault Dashboard")
        self.dashboard_window.geometry("800x600") # Reduced from 1000x700
        
        # Configure grid layout - more compact
        self.dashboard_window.grid_columnconfigure(0, weight=1)
        self.dashboard_window.grid_columnconfigure(1, weight=1)
        self.dashboard_window.grid_rowconfigure(0, weight=0) # Header row
        self.dashboard_window.grid_rowconfigure(1, weight=1) # Main content row
        self.dashboard_window.grid_rowconfigure(2, weight=0) # Bottom row
        
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
        text_count, image_count, video_count = self.parent.count_files_by_type(os.path.expanduser("~"))
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
                os.path.join(os.path.expanduser("~"), "Desktop")
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
            command=self.dashboard_window.destroy,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            height=30
        )
        return_btn.grid(row=1, column=1, padx=3, pady=3, sticky="ew")
    
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


