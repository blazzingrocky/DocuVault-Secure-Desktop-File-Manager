import tkinter as tk
from tkinter import ttk
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk
from datetime import datetime
import matplotlib.patches as mpatches
from PIL import Image, ImageTk
import sys

class Dashboard:
    def __init__(self, parent):
        self.parent = parent
        self.dashboard_window = ctk.CTkToplevel(parent.root)
        self.dashboard_window.title("DocuVault Dashboard")
        self.dashboard_window.geometry("1100x700")
        self.dashboard_window.configure(fg_color="#1a1a2e")
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main layout
        self.create_layout()
        
    def create_layout(self):
        # Create main container with two frames
        main_container = ctk.CTkFrame(self.dashboard_window, fg_color="#1a1a2e")
        main_container.pack(fill="both", expand=True)
        
        # Left sidebar
        self.sidebar = ctk.CTkFrame(main_container, fg_color="#16213e", width=250, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)
        
        # Right content area
        self.content_area = ctk.CTkFrame(main_container, fg_color="#1a1a2e", corner_radius=0)
        self.content_area.pack(side="right", fill="both", expand=True, padx=0, pady=0)
        
        # Create sidebar content
        self.create_sidebar()
        
        # Create main content
        self.create_main_content()
        
    def create_sidebar(self):
        # Logo and app name
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(30, 20))
        
        logo_label = ctk.CTkLabel(logo_frame, text="DocuVault", 
                                 font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                                 text_color="#4cc9f0")
        logo_label.pack(side="left")
        
        # Welcome message
        welcome_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        welcome_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        welcome_label = ctk.CTkLabel(welcome_frame, 
                                    text=f"Welcome, {self.parent.username}",
                                    font=ctk.CTkFont(family="Segoe UI", size=14),
                                    text_color="#f1faee")
        welcome_label.pack(anchor="w")
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10, pady=10)
        
        # Button styles
        button_hover_color = "#0f3460"
        button_fg_color = "#16213e"
        button_text_color = "#e2e2e2"
        
        # Home button
        home_btn = ctk.CTkButton(nav_frame, text="Home", 
                                corner_radius=8,
                                font=ctk.CTkFont(family="Segoe UI", size=14),
                                fg_color=button_fg_color,
                                text_color=button_text_color,
                                hover_color=button_hover_color,
                                height=40,
                                command=lambda: self.go_to_directory(os.path.expanduser("~")))
        home_btn.pack(fill="x", padx=10, pady=5)
        
        # Desktop button
        desktop_btn = ctk.CTkButton(nav_frame, text="Desktop", 
                                   corner_radius=8,
                                   font=ctk.CTkFont(family="Segoe UI", size=14),
                                   fg_color=button_fg_color,
                                   text_color=button_text_color,
                                   hover_color=button_hover_color,
                                   height=40,
                                   command=lambda: self.go_to_directory(os.path.join(os.path.expanduser("~"), "Desktop")))
        desktop_btn.pack(fill="x", padx=10, pady=5)
        
        # Current working directory button
        cwd_btn = ctk.CTkButton(nav_frame, text="Current Working Directory", 
                               corner_radius=8,
                               font=ctk.CTkFont(family="Segoe UI", size=14),
                               fg_color=button_fg_color,
                               text_color=button_text_color,
                               hover_color=button_hover_color,
                               height=40,
                               command=lambda: self.go_to_directory(os.getcwd()))
        cwd_btn.pack(fill="x", padx=10, pady=5)
        
        # File chart button
        chart_btn = ctk.CTkButton(nav_frame, text="File Type Distribution Chart", 
                                 corner_radius=8,
                                 font=ctk.CTkFont(family="Segoe UI", size=14),
                                 fg_color="#0f3460",
                                 text_color=button_text_color,
                                 hover_color="#1e5f74",
                                 height=40,
                                 command=self.show_file_type_chart)
        chart_btn.pack(fill="x", padx=10, pady=5)
        
        # Current date and time
        date_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        date_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        
        current_time = datetime.now().strftime("%B %d, %Y")
        date_label = ctk.CTkLabel(date_frame, 
                                 text=current_time,
                                 font=ctk.CTkFont(family="Segoe UI", size=12),
                                 text_color="#a9a9a9")
        date_label.pack(side="left")

        # def show_file_type_chart(self):
        #     """
        #      Show the File Type Distribution Chart in a new window.
        #     """
        #     file_types = self.parent.count_files_by_type(self.parent.current_dir)
            
        #     # Convert counts to a dictionary for chart creation
        #     file_types_dict = {
        #         ".txt": file_types[0],
        #         ".jpg": file_types[1],
        #         ".pdf": file_types[2]
        #         # Add more extensions as needed
        #     }
        #     self.create_file_type_chart(file_types_dict)

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
        }
        
        # Create the pie chart
        fig, ax = plt.subplots(figsize=(6, 5), facecolor="#1a1a2e")
        ax.set_facecolor("#1a1a2e")
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes=list(file_types_dict.values()), 
            labels=list(file_types_dict.keys()), 
            autopct='%1.1f%%', 
            startangle=90,
            colors=['#4cc9f0', '#f72585', '#7209b7']
        )
        
        # Style the chart text
        for text in texts:
            text.set_color('white')
        for autotext in autotexts:
            autotext.set_color('white')
            
        ax.set_title("File Type Distribution", color='white')
        
        # Embed the chart in a new window
        chart_window = tk.Toplevel(self.dashboard_window)
        chart_window.title("File Type Distribution")
        chart_window.geometry("500x400")
        chart_window.configure(bg="#1a1a2e")
        
        # Embed the chart
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=20)


    def create_main_content(self):
        # Header with title
        header_frame = ctk.CTkFrame(self.content_area, fg_color="transparent", height=60)
        header_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        header_label = ctk.CTkLabel(header_frame, 
                                   text="Dashboard Overview",
                                   font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                                   text_color="#f1faee")
        header_label.pack(side="left")
        
        # Current time
        time_label = ctk.CTkLabel(header_frame, 
                                 text=datetime.now().strftime("%I:%M %p"),
                                 font=ctk.CTkFont(family="Segoe UI", size=16),
                                 text_color="#a9a9a9")
        time_label.pack(side="right")
        
        # Main content with cards
        content_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create grid layout for cards
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)
        
        # File statistics card
        self.create_file_stats_card(content_frame, 0, 0)
        
        # System info card
        self.create_system_info_card(content_frame, 0, 1)
        
        # Chart card
        self.create_chart_preview_card(content_frame, 1, 0)
        
        # Quick actions card
        self.create_quick_actions_card(content_frame, 1, 1)
        
    def create_file_stats_card(self, parent, row, col):
        card = ctk.CTkFrame(parent, fg_color="#0f3460", corner_radius=10)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Card header
        header = ctk.CTkLabel(card, 
                             text="File Statistics",
                             font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                             text_color="#f1faee")
        header.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Get file counts
        home_dir = os.path.expanduser("~")
        text_count, image_count, video_count = self.parent.count_files_by_type(home_dir)
        
        # Create stats container
        stats_frame = ctk.CTkFrame(card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        # Text files stat
        self.create_stat_item(stats_frame, "Text Files", text_count, "#4cc9f0", 0)
        
        # Image files stat
        self.create_stat_item(stats_frame, "Image Files", image_count, "#f72585", 1)
        
        # Video files stat
        self.create_stat_item(stats_frame, "Video Files", video_count, "#7209b7", 2)
        
        # Total files
        total_frame = ctk.CTkFrame(card, fg_color="#1a1a2e", corner_radius=8)
        total_frame.pack(fill="x", padx=20, pady=(15, 20))
        
        total_label = ctk.CTkLabel(total_frame, 
                                  text="Total Files",
                                  font=ctk.CTkFont(family="Segoe UI", size=14),
                                  text_color="#a9a9a9")
        total_label.pack(side="left", padx=15, pady=10)
        
        total_count = ctk.CTkLabel(total_frame, 
                                  text=str(text_count + image_count + video_count),
                                  font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                  text_color="#f1faee")
        total_count.pack(side="right", padx=15, pady=10)
        
    def create_stat_item(self, parent, label_text, count, color, row):
        frame = ctk.CTkFrame(parent, fg_color="#1a1a2e", corner_radius=8, height=50)
        frame.pack(fill="x", pady=5)
        frame.pack_propagate(False)
        
        # Color indicator
        indicator = ctk.CTkFrame(frame, fg_color=color, width=4, corner_radius=2)
        indicator.pack(side="left", fill="y", padx=(15, 0), pady=10)
        
        # Label
        label = ctk.CTkLabel(frame, 
                            text=label_text,
                            font=ctk.CTkFont(family="Segoe UI", size=14),
                            text_color="#e2e2e2")
        label.pack(side="left", padx=15, pady=10)
        
        # Count
        count_label = ctk.CTkLabel(frame, 
                                  text=str(count),
                                  font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                  text_color="#f1faee")
        count_label.pack(side="right", padx=15, pady=10)
        
    def create_system_info_card(self, parent, row, col):
        card = ctk.CTkFrame(parent, fg_color="#0f3460", corner_radius=10)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Card header
        header = ctk.CTkLabel(card, 
                             text="System Information",
                             font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                             text_color="#f1faee")
        header.pack(anchor="w", padx=20, pady=(20, 15))
        
        # System info items
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        # Username
        self.create_info_item(info_frame, "Username", self.parent.username, "#4cc9f0")
        
        # Current directory
        current_dir = self.parent.current_dir
        display_dir = current_dir if len(current_dir) < 30 else "..." + current_dir[-27:]
        self.create_info_item(info_frame, "Current Directory", display_dir, "#f72585")
        
        # Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.create_info_item(info_frame, "Python Version", python_version, "#7209b7")
        
        # Current time
        self.create_info_item(info_frame, "Current Time", datetime.now().strftime("%I:%M:%S %p"), "#4361ee")
        
    def create_info_item(self, parent, label_text, value_text, color):
        frame = ctk.CTkFrame(parent, fg_color="#1a1a2e", corner_radius=8, height=50)
        frame.pack(fill="x", pady=5)
        frame.pack_propagate(False)
        
        # Color indicator
        indicator = ctk.CTkFrame(frame, fg_color=color, width=4, corner_radius=2)
        indicator.pack(side="left", fill="y", padx=(15, 0), pady=10)
        
        # Label
        label = ctk.CTkLabel(frame, 
                            text=label_text,
                            font=ctk.CTkFont(family="Segoe UI", size=14),
                            text_color="#e2e2e2")
        label.pack(side="left", padx=15, pady=10)
        
        # Value
        value_label = ctk.CTkLabel(frame, 
                                  text=value_text,
                                  font=ctk.CTkFont(family="Segoe UI", size=14),
                                  text_color="#a9a9a9")
        value_label.pack(side="right", padx=15, pady=10)
        
    def create_chart_preview_card(self, parent, row, col):
        card = ctk.CTkFrame(parent, fg_color="#0f3460", corner_radius=10)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Card header
        header = ctk.CTkLabel(card, 
                             text="File Type Distribution",
                             font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                             text_color="#f1faee")
        header.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Chart container
        chart_frame = ctk.CTkFrame(card, fg_color="#1a1a2e", corner_radius=8)
        chart_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Get file counts for chart
        home_dir = os.path.expanduser("~")
        text_count, image_count, video_count = self.parent.count_files_by_type(home_dir)
        
        # Create data for chart
        file_types_dict = {
            "Text Files": text_count,
            "Image Files": image_count,
            "Video Files": video_count
        }
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(5, 4), facecolor="#1a1a2e")
        ax.set_facecolor("#1a1a2e")
        
        # Define colors
        colors = ['#4cc9f0', '#f72585', '#7209b7']
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            file_types_dict.values(),
            labels=None,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            wedgeprops={'width': 0.6, 'edgecolor': '#1a1a2e'}
        )
        
        # Style the chart text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(9)
        
        # Add a circle at the center to create a donut chart
        centre_circle = plt.Circle((0, 0), 0.3, fc='#1a1a2e')
        ax.add_patch(centre_circle)
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        
        # Add legend
        legend_elements = [
            mpatches.Patch(facecolor=colors[0], label='Text Files'),
            mpatches.Patch(facecolor=colors[1], label='Image Files'),
            mpatches.Patch(facecolor=colors[2], label='Video Files')
        ]
        ax.legend(handles=legend_elements, loc='center', frameon=False, 
                 fontsize=9, labelcolor='white')
        
        # Embed the chart
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add view full chart button
        view_btn = ctk.CTkButton(card, text="View Full Chart", 
                                corner_radius=8,
                                font=ctk.CTkFont(family="Segoe UI", size=14),
                                fg_color="#1a1a2e",
                                text_color="#f1faee",
                                hover_color="#16213e",
                                height=40,
                                command=self.show_file_type_chart)
        view_btn.pack(padx=20, pady=(0, 20), fill="x")
        
    def create_quick_actions_card(self, parent, row, col):
        card = ctk.CTkFrame(parent, fg_color="#0f3460", corner_radius=10)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Card header
        header = ctk.CT
