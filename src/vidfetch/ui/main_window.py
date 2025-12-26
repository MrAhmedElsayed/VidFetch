"""Main application window with integrated UI design."""

import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from pathlib import Path
from typing import Optional
from io import BytesIO
import requests
import platform
import ctypes
from PIL import Image
from customtkinter import CTkImage

from ..core import YouTubeClient, VideoMetadata, PlaylistMetadata, PlaylistEntry
from ..utils import Config, resource_path
from ..version import __version__
from ..version import __version__
from .download_item import DownloadItem, DownloadTask

# Configure CustomTkinter theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def format_duration(seconds: float) -> str:
    """Format duration like YouTube (MM:SS or HH:MM:SS)."""
    if not seconds or seconds <= 0:
        return "0:00"
    
    total_seconds = int(float(seconds))
    if total_seconds < 3600:
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes}:{secs:02d}"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"


class HistoryWindow(ctk.CTkToplevel):
    """Download History Window - shows completed downloads"""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Download History - VidFetch")
        self.geometry("900x700")
        self.transient(parent)
        self.grab_set()
        
        # Inherit theme from parent
        self.parent = parent
        self.bg_color = parent.bg_color
        self.card_color = parent.card_color
        self.border_color = parent.border_color
        self.text_main = parent.text_main
        self.text_secondary = parent.text_secondary
        self.accent_blue = parent.accent_blue
        self.font_h1 = parent.font_h1
        self.font_h2 = parent.font_h2
        self.font_body = parent.font_body
        self.font_small = parent.font_small
        self.font_caps = parent.font_caps
        
        self.configure(fg_color=self.bg_color)
        
        # Load history from config (in real app, load from config/database)
        self.all_items = parent.config.get_history() if hasattr(parent.config, 'get_history') else []
        
        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Header
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Download History", font=self.font_h1, text_color=self.text_main).pack(anchor="w")
        ctk.CTkLabel(header, text="View and manage your previously downloaded videos and playlists.", 
                    font=self.font_body, text_color=self.text_secondary).pack(anchor="w", pady=(4, 0))
        
        # Toolbar
        toolbar = ctk.CTkFrame(main, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 16))
        
        # Search Input
        search_frame = ctk.CTkFrame(toolbar, fg_color=self.card_color, corner_radius=10, height=40)
        search_frame.pack(side="left", fill="x", expand=True, padx=(0, 12))
        search_frame.pack_propagate(False)
        
        search_icon = self.parent.get_icon_image("e8b6", (18, 18))
        if search_icon:
            ctk.CTkLabel(search_frame, text="", image=search_icon).pack(side="left", padx=12)
        ctk.CTkEntry(search_frame, placeholder_text="Search history...", font=self.font_body,
                    fg_color="transparent", border_width=0, text_color=self.text_main,
                    placeholder_text_color=self.text_secondary).pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Filter Button
        filter_icon = self.parent.get_icon_image("e152", (18, 18))
        ctk.CTkButton(toolbar, text="", image=filter_icon, width=40, height=40,
                     fg_color=self.card_color, hover_color=self.border_color,
                     corner_radius=10, cursor="hand2").pack(side="left", padx=(0, 12))
        
        # Clear History Button
        delete_icon = self.parent.get_icon_image("e872", (18, 18))
        ctk.CTkButton(toolbar, text="Clear History", image=delete_icon, compound="left",
                     font=self.font_body, height=40,
                     fg_color="transparent", hover_color=("#fee2e2", "#7f1d1d"), text_color="#ef4444",
                     cursor="hand2").pack(side="right")
        
        # Filter Chips
        filter_frame = ctk.CTkFrame(main, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 20))
        
        self.filter_var = ctk.StringVar(value="All")
        self.filter_btn = ctk.CTkSegmentedButton(filter_frame, values=["All", "Videos", "Playlists", "Audio"],
                                                 variable=self.filter_var, font=self.font_body,
                                                 fg_color=self.card_color, selected_color=self.accent_blue,
                                                 selected_hover_color="#0d6bc4", unselected_color=self.card_color,
                                                 unselected_hover_color=self.border_color, text_color=self.text_main,
                                                 command=self.on_filter_change)
        self.filter_btn.pack(side="left")
        
        # Scrollable Grid
        self.grid_container = ctk.CTkScrollableFrame(main, fg_color="transparent")
        self.grid_container.pack(fill="both", expand=True)
        
        # Configure grid columns
        for i in range(4):
            self.grid_container.grid_columnconfigure(i, weight=1, uniform="col")
        
        # Footer
        footer = ctk.CTkFrame(main, fg_color="transparent", height=40)
        footer.pack(fill="x", pady=(20, 0))
        self.footer_label = ctk.CTkLabel(footer, text="", font=self.font_small, text_color=self.text_secondary)
        self.footer_label.pack()
        
        # Initial render
        self.refresh_grid()
    
    def get_icon_image(self, unicode_code, size=(20, 20)):
        """Get icon image - delegate to parent"""
        return self.parent.get_icon_image(unicode_code, size)
    
    def on_filter_change(self, value):
        """Handle filter selection change"""
        self.refresh_grid()
    
    def refresh_grid(self):
        """Refresh the grid based on current filter"""
        # Clear existing cards
        for widget in self.grid_container.winfo_children():
            widget.destroy()
        
        # Get current filter
        filter_val = self.filter_var.get().lower()
        
        # Filter items
        if filter_val == "all":
            items = self.all_items
        elif filter_val == "videos":
            items = [i for i in self.all_items if i.get("type") == "video"]
        elif filter_val == "playlists":
            items = [i for i in self.all_items if i.get("type") == "playlist"]
        elif filter_val == "audio":
            items = [i for i in self.all_items if i.get("type") == "audio"]
        else:
            items = self.all_items
        
        # Show empty state or create cards
        if not items:
            # Empty state
            empty = ctk.CTkFrame(self.grid_container, fg_color="transparent")
            empty.grid(row=0, column=0, columnspan=4, pady=60)
            
            icon = self.parent.get_icon_image("e889", (64, 64))
            if icon:
                ctk.CTkLabel(empty, text="", image=icon).pack(pady=(0, 16))
            ctk.CTkLabel(empty, text="No Download History", font=self.font_h2, text_color=self.text_main).pack()
            ctk.CTkLabel(empty, text="Your completed downloads will appear here.", 
                        font=self.font_body, text_color=self.text_secondary).pack(pady=(8, 0))
        else:
            for idx, item in enumerate(items):
                row = idx // 4
                col = idx % 4
                self.create_history_card(self.grid_container, item, row, col)
        
        # Update footer
        if self.footer_label:
            self.footer_label.configure(text=f"Showing {len(items)} of {len(self.all_items)} downloads")
    
    def create_history_card(self, parent, data, row, col):
        """Create a single history card"""
        card = ctk.CTkFrame(parent, fg_color=self.card_color, corner_radius=12, 
                           border_width=1, border_color=self.border_color)
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        
        # Thumbnail placeholder
        thumb = ctk.CTkFrame(card, fg_color=data.get("color", "#333"), height=100, corner_radius=8)
        thumb.pack(fill="x", padx=8, pady=8)
        thumb.pack_propagate(False)
        
        # Duration badge
        if "duration" in data:
            ctk.CTkLabel(thumb, text=data["duration"], font=("Helvetica", 9, "bold"),
                        fg_color="#000000", text_color="white", corner_radius=4, padx=4).place(relx=0.95, rely=0.9, anchor="se")
        
        # Type icon
        type_icon_map = {"audio": "e3a1", "video": "e02c", "playlist": "e05f"}
        type_colors = {"audio": "#3b82f6", "video": "#ef4444", "playlist": "#8b5cf6"}
        icon_code = type_icon_map.get(data.get("type", "video"), "e02c")
        icon_bg = type_colors.get(data.get("type", "video"), "#ef4444")
        type_icon = self.parent.get_icon_image(icon_code, (14, 14))
        if type_icon:
            icon_label = ctk.CTkLabel(thumb, text="", image=type_icon, fg_color=icon_bg, 
                        width=24, height=24, corner_radius=6)
            icon_label.place(x=8, y=8)
        
        # Content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Title row
        title_row = ctk.CTkFrame(content, fg_color="transparent")
        title_row.pack(fill="x")
        
        ctk.CTkLabel(title_row, text=data.get("title", "Unknown"), font=self.font_body, text_color=self.text_main,
                    wraplength=150, anchor="w", justify="left").pack(side="left", fill="x", expand=True)
        more_icon = self.parent.get_icon_image("e5d4", (16, 16))
        if more_icon:
            ctk.CTkButton(title_row, text="", image=more_icon, width=24, height=24,
                         fg_color="transparent", hover_color=self.border_color,
                         cursor="hand2").pack(side="right")
        
        # Meta row
        meta = ctk.CTkFrame(content, fg_color="transparent")
        meta.pack(fill="x", pady=(8, 0))
        
        meta_left = ctk.CTkFrame(meta, fg_color="transparent")
        meta_left.pack(side="left")
        
        if "size" in data and "format" in data:
            ctk.CTkLabel(meta_left, text=f"{data['size']} • {data['format']}", font=self.font_small, 
                        text_color=self.text_secondary).pack(anchor="w")
        if "date" in data:
            ctk.CTkLabel(meta_left, text=data["date"], font=self.font_small, 
                        text_color=self.text_secondary).pack(anchor="w")
        
        # Folder button
        folder_icon = self.parent.get_icon_image("e2c8", (18, 18))
        if folder_icon:
            ctk.CTkButton(meta, text="", image=folder_icon, width=32, height=32,
                         fg_color=("#e0f2fe", "#1e3a5f"), hover_color=self.accent_blue, 
                         corner_radius=50, cursor="hand2").pack(side="right")


class SettingsWindow(ctk.CTkToplevel):
    """Settings Window - app configuration"""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Settings - VidFetch")
        self.geometry("800x700")
        self.transient(parent)
        self.grab_set()
        
        # Inherit theme from parent
        self.parent = parent
        self.bg_color = parent.bg_color
        self.card_color = parent.card_color
        self.border_color = parent.border_color
        self.text_main = parent.text_main
        self.text_secondary = parent.text_secondary
        self.accent_blue = parent.accent_blue
        self.font_h1 = parent.font_h1
        self.font_h2 = parent.font_h2
        self.font_body = parent.font_body
        self.font_small = parent.font_small
        
        self.configure(fg_color=self.bg_color)
        
        # Main scrollable container
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Header
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 24))
        
        ctk.CTkLabel(header, text="Settings", font=self.font_h1, text_color=self.text_main).pack(anchor="w")
        ctk.CTkLabel(header, text="Customize your VidFetch experience and preferences.", 
                    font=self.font_body, text_color=self.text_secondary).pack(anchor="w", pady=(4, 0))
        
        # --- Downloads Section ---
        self.create_section_header(main, "e2c0", "Downloads")
        
        downloads_card = ctk.CTkFrame(main, fg_color=self.card_color, corner_radius=12, 
                                      border_width=1, border_color=self.border_color)
        downloads_card.pack(fill="x", pady=(0, 24))
        
        downloads_inner = ctk.CTkFrame(downloads_card, fg_color="transparent")
        downloads_inner.pack(fill="x", padx=24, pady=20)
        
        # Row 1: Video Quality + Audio Format
        row1 = ctk.CTkFrame(downloads_inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 16))
        
        # Video Quality
        vq_frame = ctk.CTkFrame(row1, fg_color="transparent")
        vq_frame.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ctk.CTkLabel(vq_frame, text="Default Video Quality", font=self.font_body, 
                    text_color=self.text_main).pack(anchor="w", pady=(0, 8))
        self.video_quality = ctk.CTkOptionMenu(vq_frame, values=["Best Available (4K/8K)", "Full HD (1080p)", "HD (720p)", "Data Saver (480p)"],
                                               font=self.font_body, fg_color=self.bg_color, button_color=self.border_color,
                                               button_hover_color=self.accent_blue, dropdown_fg_color=self.card_color,
                                               dropdown_hover_color=self.border_color, height=44, corner_radius=10)
        self.video_quality.pack(fill="x")
        
        # Audio Format
        af_frame = ctk.CTkFrame(row1, fg_color="transparent")
        af_frame.pack(side="left", fill="x", expand=True, padx=(12, 0))
        ctk.CTkLabel(af_frame, text="Default Audio Format", font=self.font_body, 
                    text_color=self.text_main).pack(anchor="w", pady=(0, 8))
        self.audio_format = ctk.CTkOptionMenu(af_frame, values=["MP3 (320kbps)", "MP3 (128kbps)", "M4A (AAC)", "WAV (Lossless)"],
                                              font=self.font_body, fg_color=self.bg_color, button_color=self.border_color,
                                              button_hover_color=self.accent_blue, dropdown_fg_color=self.card_color,
                                              dropdown_hover_color=self.border_color, height=44, corner_radius=10)
        self.audio_format.pack(fill="x")
        
        # Row 2: Download Location
        ctk.CTkLabel(downloads_inner, text="Download Location", font=self.font_body, 
                    text_color=self.text_main).pack(anchor="w", pady=(0, 8))
        
        loc_row = ctk.CTkFrame(downloads_inner, fg_color="transparent")
        loc_row.pack(fill="x")
        
        loc_input = ctk.CTkFrame(loc_row, fg_color=self.bg_color, corner_radius=10, height=44,
                                 border_width=1, border_color=self.border_color)
        loc_input.pack(side="left", fill="x", expand=True, padx=(0, 12))
        loc_input.pack_propagate(False)
        
        folder_icon = self.parent.get_icon_image("e2c7", (18, 18))
        if folder_icon:
            ctk.CTkLabel(loc_input, text="", image=folder_icon).pack(side="left", padx=12)
        
        self.path_var = tk.StringVar(value=str(parent.config.download_path))
        path_label = ctk.CTkLabel(loc_input, textvariable=self.path_var, font=self.font_body, 
                    text_color=self.text_secondary)
        path_label.pack(side="left", fill="x", expand=True)
        
        def browse_path():
            d = filedialog.askdirectory()
            if d:
                self.path_var.set(d)
                parent.config.set_download_path(d)
        
        ctk.CTkButton(loc_row, text="Change Folder", font=self.font_body, height=44,
                     fg_color=("#e0f2fe", "#1e3a5f"), hover_color=self.accent_blue,
                     text_color=self.accent_blue, corner_radius=10, cursor="hand2",
                     command=browse_path).pack(side="right")
        
        # --- Appearance & Notifications Row ---
        two_col = ctk.CTkFrame(main, fg_color="transparent")
        two_col.pack(fill="x", pady=(0, 24))
        two_col.grid_columnconfigure(0, weight=1)
        two_col.grid_columnconfigure(1, weight=1)
        
        # --- Appearance Section (Left) ---
        app_col = ctk.CTkFrame(two_col, fg_color="transparent")
        app_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        
        self.create_section_header(app_col, "e40a", "Appearance")
        
        app_card = ctk.CTkFrame(app_col, fg_color=self.card_color, corner_radius=12, 
                               border_width=1, border_color=self.border_color)
        app_card.pack(fill="both", expand=True)
        
        app_inner = ctk.CTkFrame(app_card, fg_color="transparent")
        app_inner.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Theme Selection
        ctk.CTkLabel(app_inner, text="App Theme", font=self.font_body, text_color=self.text_main).pack(anchor="w", pady=(0, 12))
        
        theme_row = ctk.CTkFrame(app_inner, fg_color="transparent")
        theme_row.pack(fill="x", pady=(0, 20))
        
        self.theme_var = ctk.StringVar(value="Dark")
        themes = [("Light", "e518"), ("Dark", "e51c"), ("System", "e322")]
        
        for name, icon in themes:
            self.create_theme_option(theme_row, name, icon)
        
        # --- Notifications Section (Right) ---
        notif_col = ctk.CTkFrame(two_col, fg_color="transparent")
        notif_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        
        self.create_section_header(notif_col, "e7f4", "Notifications")
        
        notif_card = ctk.CTkFrame(notif_col, fg_color=self.card_color, corner_radius=12, 
                                 border_width=1, border_color=self.border_color)
        notif_card.pack(fill="both", expand=True)
        
        notif_inner = ctk.CTkFrame(notif_card, fg_color="transparent")
        notif_inner.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Toggle options
        self.create_toggle_option(notif_inner, "Download Completed", "Show notification when done", True)
        self.create_toggle_option(notif_inner, "Download Failed", "Notify if download fails", True)
        self.create_toggle_option(notif_inner, "Sound Effects", "Play sound on completion", False)
        
        # --- Footer ---
        footer = ctk.CTkFrame(main, fg_color="transparent")
        footer.pack(fill="x", pady=(16, 0))
        
        # Reset button (left)
        ctk.CTkButton(footer, text="Reset to Defaults", font=self.font_body, height=40,
                     fg_color="transparent", hover_color=("#fee2e2", "#7f1d1d"), 
                     text_color=self.text_secondary, cursor="hand2").pack(side="left")
        
        # Save/Cancel buttons (right)
        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.pack(side="right")
        
        ctk.CTkButton(btn_row, text="Cancel", font=self.font_body, height=40, width=100,
                     fg_color="transparent", hover_color=self.border_color,
                     text_color=self.text_main, border_width=1, border_color=self.border_color,
                     corner_radius=10, cursor="hand2", command=self.destroy).pack(side="left", padx=(0, 12))
        
        def save_settings():
            parent.config.set_download_path(self.path_var.get())
            self.destroy()
        
        ctk.CTkButton(btn_row, text="Save Changes", font=self.font_body, height=40, width=120,
                     fg_color=self.accent_blue, hover_color="#0d6bc4",
                     text_color="white", corner_radius=10, cursor="hand2",
                     command=save_settings).pack(side="left")
    
    def create_section_header(self, parent, icon_code, title):
        """Create a section header with icon"""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        header_icon = self.parent.get_icon_image(icon_code, (20, 20))
        if header_icon:
            ctk.CTkLabel(header, text="", image=header_icon).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header, text=title, font=self.font_h2, text_color=self.text_main).pack(side="left")
    
    def create_theme_option(self, parent, name, icon):
        """Create a theme selection option"""
        is_selected = self.theme_var.get() == name
        
        frame = ctk.CTkFrame(parent, fg_color=self.bg_color if not is_selected else ("#e0f2fe", "#1e3a5f"), 
                            corner_radius=10, border_width=1, 
                            border_color=self.accent_blue if is_selected else self.border_color,
                            width=80, height=70)
        frame.pack(side="left", padx=(0, 8))
        frame.pack_propagate(False)
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        
        theme_icon = self.parent.get_icon_image(icon, (24, 24))
        if theme_icon:
            ctk.CTkLabel(inner, text="", image=theme_icon).pack()
        ctk.CTkLabel(inner, text=name, font=self.font_small, text_color=self.text_main).pack(pady=(4, 0))
        
        # Make clickable
        def set_theme(n=name):
            self.theme_var.set(n)
            for widget in parent.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    widget.configure(fg_color=self.bg_color, border_color=self.border_color)
            frame.configure(fg_color=("#e0f2fe", "#1e3a5f"), border_color=self.accent_blue)
        
        frame.bind("<Button-1>", lambda e, n=name: set_theme(n))
        for widget in frame.winfo_children():
            widget.bind("<Button-1>", lambda e, n=name: set_theme(n))
        frame.configure(cursor="hand2")
    
    def create_toggle_option(self, parent, title, description, default_on):
        """Create a toggle switch option"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))
        
        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(text_col, text=title, font=self.font_body, text_color=self.text_main).pack(anchor="w")
        ctk.CTkLabel(text_col, text=description, font=self.font_small, text_color=self.text_secondary, 
                    wraplength=200).pack(anchor="w")
        
        switch = ctk.CTkSwitch(row, text="", onvalue=True, offvalue=False,
                              button_color=self.accent_blue, button_hover_color="#0d6bc4",
                              progress_color=self.accent_blue, fg_color=self.border_color)
        switch.pack(side="right")
        if default_on:
            switch.select()
    
    def get_icon_image(self, unicode_code, size=(20, 20)):
        """Get icon image - delegate to parent"""
        return self.parent.get_icon_image(unicode_code, size)


class VidFetchApp(ctk.CTk):
    """Main application window for VidFetch."""
    
    def __init__(self):
        super().__init__()
        try:
            self.title(f"VidFetch v{__version__}")
            self.geometry("1000x800")
            ctk.set_appearance_mode("dark")
        except Exception as e:
            import logging
            logging.error(f"Error in VidFetchApp.__init__: {e}", exc_info=True)
            raise
        
        # Set Window Icon (cross-platform)
        try:
            icon_path = resource_path("assets/logo.ico")
            is_mac = platform.system() == 'Darwin'
            
            if is_mac:
                icon_path_png = resource_path("assets/logo.png")
                if icon_path_png.exists():
                    try:
                        photo = tk.PhotoImage(file=str(icon_path_png))
                        self.iconphoto(True, photo)
                    except Exception as e:
                        pass
            else:
                if icon_path.exists():
                    icon_str = str(icon_path).replace('/', '\\')
                    self.iconbitmap(icon_str)
        except Exception:
            pass
        
        try:
            if hasattr(ctypes, 'windll'):
                myappid = f"com.vidfetch.app.{__version__}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # Theme colors (Light, Dark) tuples
        self.accent_blue = "#137fec"
        self.accent_green = "#22c55e"
        self.bg_color = ("#f6f7f8", "#101922")
        self.header_color = ("#ffffff", "#101922")
        self.card_color = ("#ffffff", "#1e293b")
        self.border_color = ("#e5e7eb", "#1e293b")
        self.col_primary = self.accent_blue
        self.col_success = "#22c55e"
        self.col_error = "#ef4444"
        self.text_main = ("#111827", "#ffffff")
        self.text_secondary = ("#6b7280", "#94a3b8")

        # Setup fonts and icons
        self.setup_fonts()
        self.setup_icons()

        # Data
        self.current_metadata: Optional[VideoMetadata] = None
        self.current_playlist: Optional[PlaylistMetadata] = None
        self.youtube = YouTubeClient()
        self.config = Config()
        self.format_mode = "video"  # "video" or "audio"
        self.download_tasks = []  # Track download tasks (models)
        
        # Main Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.create_header()
        self.create_main_content()
        self.create_footer() 
        # Controls


    def add_single(self, fmt, best_audio=None):
        # ...
        try:
            # ... (path calculation same) ...
            safe_title = "".join([c for c in self.current_metadata.title if c.isalnum() or c in (' ', '-', '_')]).strip()
            filename = f"{safe_title}_{fmt.resolution}.{fmt.ext}"
            save_path = self.config.download_path / filename
            
            # Create Task
            task = DownloadTask(
                 self.current_metadata.title, fmt.url,
                 best_audio.url if best_audio else None, save_path,
                 thumb_url=self.current_metadata.thumbnail_url,
                 headers=fmt.http_headers
            )
            self.download_tasks.append(task)
            task.start()
            
            self.show_view("downloads")
            
        except Exception as e:
            # ...
            pass

    def update_downloads_display(self):
        # This might not be needed anymore or just updates the counter in sidebar if exists?
        pass

    def pause_all_downloads(self):
        for task in self.download_tasks:
            if not task.is_paused:
                task.toggle_pause()

    def resume_all_downloads(self):
        for task in self.download_tasks:
            if task.is_paused:
                task.toggle_pause()
        
        # Main Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.create_header()
        self.create_main_content()
        self.create_footer()
    
    def setup_fonts(self):
        """Standardized font management - using Helvetica system font"""
        self.font_h1 = ctk.CTkFont(family="Helvetica", size=48, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Helvetica", size=18, weight="bold")
        self.font_body = ctk.CTkFont(family="Helvetica", size=15)
        self.font_small = ctk.CTkFont(family="Helvetica", size=13)
        self.font_caps = ctk.CTkFont(family="Helvetica", size=11, weight="bold")
    
    def setup_icons(self):
        """Setup icon mapping and load icon images"""
        # Mapping from Unicode codes to file names (Material Symbols Rounded)
        self.icon_map = {
            "e8b6": "search",
            "e152": "filter_list",
            "e872": "delete",
            "e3a1": "music_note",
            "e02c": "videocam",
            "e05f": "playlist_play",
            "e5d4": "more_vert",
            "e2c8": "folder",
            "e2c7": "folder",
            "e2c0": "download",
            "e941": "download",
            "e40a": "palette",
            "e518": "light_mode",
            "e51c": "moon_stars",
            "e322": "settings_brightness",
            "e7f4": "notifications",
            "e037": "play_arrow",
            "e038": "video_library",
            "e04a": "video_library",
            "f090": "download",
            "e889": "history",
            "e8b8": "settings",
            "e039": "play_circle",
            "e034": "pause_circle",
            "e876": "check_circle",
            "e1db": "database",
            "e916": "event_available",
            "e8b5": "calendar_check",
            "e5cd": "close_small",
            "e157": "add_link",
            "e14f": "content_paste",
        }
        
        # Cache for loaded icons
        self._icon_cache = {}
    
    def get_icon_image(self, unicode_code, size=(20, 20)):
        """Get icon as CTkImage from PNG file with proper light/dark mode support"""
        # Extract code from unicode string if needed
        if unicode_code.startswith("\\u"):
            code = unicode_code[2:]
        elif unicode_code.startswith("u"):
            code = unicode_code[1:]
        else:
            code = unicode_code.lower()
        
        # Get icon name from mapping
        icon_name = self.icon_map.get(code)
        if not icon_name:
            return None
        
        # Create cache key
        cache_key = f"{icon_name}_{size[0]}_{size[1]}"
        
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        # Load icon files using resource_path
        try:
            icons_dir = resource_path("assets/icons")
            
            # Find dark icon (for light mode) - color code 1F1F1F
            dark_icon_file = None
            for file in icons_dir.glob(f"{icon_name}_*1F1F1F*.png"):
                dark_icon_file = file
                break
            
            # Find light icon (for dark mode) - color code E0E0E0 or FFFFFF
            light_icon_file = None
            for file in icons_dir.glob(f"{icon_name}_*E0E0E0*.png"):
                light_icon_file = file
                break
            if not light_icon_file:
                for file in icons_dir.glob(f"{icon_name}_*FFFFFF*.png"):
                    light_icon_file = file
                    break
            
            # Fallback: if no color-coded files found, try any file with icon name
            if not dark_icon_file:
                for file in icons_dir.glob(f"{icon_name}_*.png"):
                    if "E0E0E0" not in file.name and "FFFFFF" not in file.name:
                        dark_icon_file = file
                        break
            
            # Special fallback for content_paste -> content_copy
            if not dark_icon_file and icon_name == "content_paste":
                for file in icons_dir.glob("content_copy_*1F1F1F*.png"):
                    dark_icon_file = file
                    break
                if not light_icon_file:
                    for file in icons_dir.glob("content_copy_*E0E0E0*.png"):
                        light_icon_file = file
                        break
                    if not light_icon_file:
                        for file in icons_dir.glob("content_copy_*FFFFFF*.png"):
                            light_icon_file = file
                            break
            
            if not dark_icon_file or not dark_icon_file.exists():
                return None
            
            # Load images with PIL
            dark_img = Image.open(str(dark_icon_file))
            
            if light_icon_file and light_icon_file.exists():
                light_img = Image.open(str(light_icon_file))
            else:
                light_img = dark_img
            
            # Create CTkImage
            icon_image = ctk.CTkImage(
                light_image=dark_img,
                dark_image=light_img,
                size=size
            )
            
            # Cache it
            self._icon_cache[cache_key] = icon_image
            return icon_image
            
        except Exception as e:
            return None

    def go_home(self):
        """Navigate back to the home page"""
        self.clear_content()
        self.create_main_content()

    def create_header(self):
        """Create the header with new design"""
        # Header container with proper borders
        header_container = ctk.CTkFrame(self, corner_radius=0, fg_color=self.header_color)
        header_container.grid(row=0, column=0, sticky="ew")
        
        # Top border
        top_border = ctk.CTkFrame(header_container, height=1, corner_radius=0, fg_color=self.border_color)
        top_border.pack(fill="x")
        
        # Main header with increased height
        self.header = ctk.CTkFrame(header_container, height=80, corner_radius=0, fg_color=self.header_color)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        
        # Bottom border
        bottom_border = ctk.CTkFrame(header_container, height=1, corner_radius=0, fg_color=self.border_color)
        bottom_border.pack(fill="x")
        
        # Logo side
        logo_box = ctk.CTkFrame(self.header, fg_color="transparent")
        logo_box.pack(side="left", padx=32, pady=20)
        
        # Logo using resource_path
        try:
            img_path = resource_path("assets/logo.png")
            if img_path.exists():
                pil_img = Image.open(str(img_path))
                logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(36, 36))
                self.logo_label = ctk.CTkLabel(logo_box, text="", image=logo_img, width=36, height=36)
            else:
                self.logo_label = ctk.CTkLabel(logo_box, text="", width=36, height=36)
                fallback_img = self.get_icon_image("e038", (36, 36))
                if fallback_img: 
                    self.logo_label.configure(image=fallback_img)
        except Exception as e:
            self.logo_label = ctk.CTkLabel(logo_box, text="", width=36, height=36)
            fallback_img = self.get_icon_image("e038", (36, 36))
            if fallback_img: 
                self.logo_label.configure(image=fallback_img)
        
        self.logo_label.pack(side="left", padx=(0, 12))
        self.logo_label.bind("<Button-1>", lambda e: self.go_home())
        self.logo_label.configure(cursor="hand2")
        
        title_label = ctk.CTkLabel(logo_box, text="VidFetch", font=self.font_h2, text_color=self.text_main)
        title_label.pack(side="left")
        title_label.bind("<Button-1>", lambda e: self.go_home())
        title_label.configure(cursor="hand2")

        # Buttons side
        actions = ctk.CTkFrame(self.header, fg_color="transparent")
        actions.pack(side="right", padx=32, pady=20)

        # Theme toggle
        theme_icon = self.get_icon_image("e51c", (20, 20))
        self.theme_btn = ctk.CTkButton(actions, text="", image=theme_icon, width=40, height=40,
                                      corner_radius=10, fg_color="transparent",
                                      hover_color=self.bg_color, command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=6)
        
        # Downloads icon
        download_icon = self.get_icon_image("f090", (20, 20))
        ctk.CTkButton(actions, text="", image=download_icon, width=40, height=40,
                     corner_radius=10, fg_color="transparent",
                     hover_color=self.bg_color, command=self.show_downloads_view).pack(side="left", padx=6)
        
        # History button
        history_icon = self.get_icon_image("e889", (20, 20))
        ctk.CTkButton(actions, text="", image=history_icon, width=40, height=40,
                     corner_radius=10, fg_color="transparent",
                     hover_color=self.bg_color, command=self.show_history_view).pack(side="left", padx=6)
        
        # Settings button
        settings_icon = self.get_icon_image("e8b8", (20, 20))
        ctk.CTkButton(actions, text="", image=settings_icon, width=40, height=40,
                     corner_radius=10, fg_color="transparent",
                     hover_color=self.bg_color, command=self.show_settings_view).pack(side="left", padx=6)
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        # Update theme button icon
        theme_icon_code = "e518" if new_mode == "Light" else "e51c"
        new_theme_icon = self.get_icon_image(theme_icon_code, (20, 20))
        if new_theme_icon:
            self.theme_btn.configure(image=new_theme_icon)
    
    def show_history_view(self):
        """Open the History Window dialog"""
        HistoryWindow(self)

    def show_settings_view(self):
        """Open the Settings Window dialog"""
        SettingsWindow(self)
    
    def show_downloads_view(self):
        """Show downloads view"""
        self.clear_content()
        self.show_view("downloads")

    def create_main_content(self):
        """Create main content area with new design"""
        # Use frame instead of scrollable frame to prevent always-visible scrollbar
        main_container = ctk.CTkFrame(self, fg_color=self.bg_color, corner_radius=0)
        main_container.grid(row=1, column=0, sticky="nsew")
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # Only use scrollable frame if content exceeds viewport
        self.main_view = ctk.CTkScrollableFrame(main_container, fg_color=self.bg_color, corner_radius=0)
        self.main_view.grid(row=0, column=0, sticky="nsew")
        self.main_view.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(self.main_view, fg_color="transparent")
        content.grid(row=0, column=0, pady=60, padx=20)

        # 1. Hero
        hero = ctk.CTkFrame(content, fg_color="transparent")
        hero.pack(fill="x", pady=(0, 40))
        title_box = ctk.CTkFrame(hero, fg_color="transparent")
        title_box.pack()
        ctk.CTkLabel(title_box, text="VidFetch ", font=self.font_h1, text_color=self.accent_blue, anchor="e").pack(side="left")
        ctk.CTkLabel(title_box, text="Video Downloader", font=self.font_h1, text_color=self.text_main).pack(side="left")
        ctk.CTkLabel(hero, text="Download videos and playlists from various platforms in 4K, HD, or MP3 audio instantly.\nNo registration required.",
                     font=self.font_body, text_color=self.text_secondary, justify="center").pack(pady=15)

        # 2. Input Card with complete border
        card_container = ctk.CTkFrame(content, fg_color="transparent")
        card_container.pack(fill="x", padx=10)
        
        card = ctk.CTkFrame(card_container, fg_color=self.card_color, corner_radius=20, 
                           border_width=2, border_color=self.border_color)
        card.pack(fill="x")
        
        # Search Row
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=30, pady=(30, 20))
        
        # Input Container - Single Frame with Border
        input_container = ctk.CTkFrame(row, fg_color="transparent")
        input_container.pack(side="left", expand=True, fill="x", padx=(0, 15))
        
        input_bg = ctk.CTkFrame(input_container, fg_color=self.header_color, 
                                border_width=1, border_color=self.border_color, 
                                corner_radius=12, height=54)
        input_bg.pack(fill="x")
        input_bg.pack_propagate(False)
        
        # Link icon
        link_icon = self.get_icon_image("e157", (18, 18))
        if link_icon:
            ctk.CTkLabel(input_bg, text="", image=link_icon).pack(side="left", padx=15)
        else:
            ctk.CTkLabel(input_bg, text="🔗", font=self.font_body, text_color=self.text_secondary).pack(side="left", padx=15)
        
        self.url_var = ctk.StringVar()
        self.url_entry = ctk.CTkEntry(input_bg, textvariable=self.url_var, placeholder_text="Paste video link here...", 
                                      border_width=0, fg_color="transparent", font=self.font_body)
        self.url_entry.pack(side="left", expand=True, fill="both", pady=2)
        self.url_entry.bind('<Return>', lambda e: self.fetch_info())
        
        paste_icon_main = self.get_icon_image("e14f", (18, 18))
        if paste_icon_main:
            ctk.CTkButton(input_bg, text="", image=paste_icon_main, width=32, height=32,
                         corner_radius=8, fg_color="transparent",
                         hover_color=self.border_color, command=self.paste_clip).pack(side="right", padx=8)

        # Get Video Button
        btn_container = ctk.CTkFrame(row, fg_color="transparent")
        btn_container.pack(side="right")
        
        self.play_icon = self.get_icon_image("e037", (48, 48))
        self.download_icon = self.get_icon_image("f090", (20, 20))
        get_video_icon = self.get_icon_image("e8b6", (20, 20))

        self.get_btn = ctk.CTkButton(btn_container, text="Get Video", font=self.font_h2, 
                                     height=56, width=180, fg_color=self.accent_blue, 
                                     hover_color="#0d6bc4", corner_radius=12,
                                     image=get_video_icon, compound="left",
                                     command=self.fetch_info)
        self.get_btn.pack()

        # Features Row
        feats = ctk.CTkFrame(card, fg_color="transparent")
        feats.pack(pady=(0, 30))
        check_feature_icon = self.get_icon_image("e876", (16, 16))
        for txt in ["Unlimited Downloads", "High Speed Converter", "No Registration"]:
            f = ctk.CTkFrame(feats, fg_color="transparent")
            f.pack(side="left", padx=15)
            if check_feature_icon:
                ctk.CTkLabel(f, text="", image=check_feature_icon).pack(side="left", padx=5)
            ctk.CTkLabel(f, text=txt, font=self.font_small, text_color=self.text_secondary).pack(side="left")

        # 3. Recents
        self.create_recents(content)
        
        self.results_view = None
    
    def paste_clip(self):
        """Paste URL from clipboard into the URL entry field"""
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.url_var.set(clipboard_text)
        except Exception as e:
            pass
    
    def create_recents(self, parent):
        """Create recent downloads section"""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", pady=30, padx=10)
        
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(head, text="RECENT DOWNLOADS", font=self.font_caps, text_color=self.text_secondary).pack(side="left")
        
        # Load recent items from config history
        recent_items = self.config.get_history()[:3] if hasattr(self.config, 'get_history') else []
        
        if recent_items:
            clear_btn = ctk.CTkButton(head, text="Clear All", width=80, height=28, 
                                     fg_color="transparent", text_color=self.accent_blue, 
                                     font=self.font_caps, hover_color=self.card_color)
            clear_btn.pack(side="right")
            
            for item in recent_items:
                f = ctk.CTkFrame(box, fg_color=self.card_color, height=72, corner_radius=12, 
                               border_width=1, border_color=self.border_color)
                f.pack(fill="x", pady=4)
                f.pack_propagate(False)

                # Placeholder Icon
                thumb_icon = self.get_icon_image("e04a", (32, 32))
                
                img_l = ctk.CTkLabel(f, text="", width=48, height=48, fg_color=self.bg_color, corner_radius=8,
                                   image=thumb_icon)
                img_l.pack(side="left", padx=14, pady=12)
                
                info = ctk.CTkFrame(f, fg_color="transparent")
                info.pack(side="left", fill="both", expand=True, pady=14, padx=8)
                ctk.CTkLabel(info, text=item.get('title', 'Unknown'), font=self.font_small, text_color=self.text_main, anchor="w").pack(fill="x", anchor="w")
                ctk.CTkLabel(info, text=f"{item.get('format', 'MP4')} • {item.get('size', 'Unknown')}", font=self.font_caps, text_color=self.text_secondary, anchor="w").pack(fill="x", anchor="w", pady=(2, 0))

                download_btn_icon = self.get_icon_image("e2c7", (20, 20))
                ctk.CTkButton(f, text="", image=download_btn_icon, width=40, height=40,
                             corner_radius=10, fg_color="transparent",
                             hover_color=self.bg_color).pack(side="right", padx=15)
        else:
            # Empty state for recents
            empty = ctk.CTkFrame(box, fg_color=self.card_color, corner_radius=12, 
                               border_width=1, border_color=self.border_color)
            empty.pack(fill="x", pady=10)
            
            inner = ctk.CTkFrame(empty, fg_color="transparent")
            inner.pack(pady=30)
            
            icon = self.get_icon_image("e889", (48, 48))
            if icon:
                ctk.CTkLabel(inner, text="", image=icon).pack(pady=(0, 12))
            ctk.CTkLabel(inner, text="No Recent Downloads", font=self.font_body, text_color=self.text_main).pack()
            ctk.CTkLabel(inner, text="Your download history will appear here", 
                        font=self.font_small, text_color=self.text_secondary).pack(pady=(4, 0))
    
    def clear_content(self):
        """Clear the main content area"""
        for widget in self.main_view.winfo_children():
            widget.destroy()
        # Reset scroll to top
        try:
            self.main_view._parent_canvas.yview_moveto(0)
        except:
            pass
    
    def create_empty_state(self, parent, icon_code, title, description, button_text=None, button_command=None):
        """Create a consistent empty state UI"""
        container = ctk.CTkFrame(parent, fg_color=self.card_color, corner_radius=16,
                                border_width=1, border_color=self.border_color)
        container.pack(fill="x", pady=20)
        
        inner = ctk.CTkFrame(container, fg_color="transparent")
        inner.pack(pady=60)
        
        # Icon
        icon = self.get_icon_image(icon_code, (64, 64))
        if icon:
            ctk.CTkLabel(inner, text="", image=icon).pack(pady=(0, 20))
        
        # Title
        ctk.CTkLabel(inner, text=title, font=self.font_h2, text_color=self.text_main).pack()
        
        # Description
        ctk.CTkLabel(inner, text=description, font=self.font_body, 
                    text_color=self.text_secondary, wraplength=400).pack(pady=(8, 0))
        
        # Optional action button
        if button_text and button_command:
            ctk.CTkButton(inner, text=button_text, font=self.font_body, height=44,
                         fg_color=self.accent_blue, hover_color="#0d6bc4",
                         corner_radius=10, command=button_command).pack(pady=(20, 0))

    def show_downloads_view(self):
        """Show downloads view with new card-based design"""
        self.clear_content()
        
        # Main Layout Container (Centered max-width like Results View)
        layout = ctk.CTkFrame(self.main_view, fg_color="transparent", width=1000)
        layout.grid(row=0, column=0, pady=40, padx=20)
        
        # --- Header Section ---
        header = ctk.CTkFrame(layout, fg_color="transparent")
        header.pack(fill="x", pady=(0, 32))
        
        # Title Group
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        
        active_count = len([t for t in self.download_tasks if t.is_downloading or t.is_paused])
        ctk.CTkLabel(title_box, text=f"Active Downloads ({active_count})", font=self.font_h1, text_color=self.text_main).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Monitor progress, manage queue, and control speed.", 
                    font=self.font_body, text_color=self.text_secondary).pack(anchor="w", pady=(4, 0))
        
        # Controls
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(side="right")
        
        # Pause All
        pause_all = ctk.CTkButton(controls, text="Pause All", font=self.font_body, height=40,
                                 fg_color=self.card_color, hover_color=self.border_color, text_color=self.text_main,
                                 image=self.get_icon_image("e034", (20, 20)), compound="left", cursor="hand2",
                                 command=self.pause_all_downloads)
        pause_all.pack(side="left", padx=12)
        
        # Resume All
        resume_all = ctk.CTkButton(controls, text="Resume All", font=self.font_body, height=40,
                                  fg_color=self.card_color, hover_color=self.border_color, text_color=self.text_main,
                                  image=self.get_icon_image("e037", (20, 20)), compound="left", cursor="hand2",
                                  command=self.resume_all_downloads)
        resume_all.pack(side="left")

        # --- Cards container ---
        self.downloads_container = ctk.CTkFrame(layout, fg_color="transparent")
        self.downloads_container.pack(fill="both", expand=True)
        
        if self.download_tasks:
            for task in self.download_tasks:
                item = DownloadItem(self.downloads_container, task)
                item.pack(fill='x', pady=8)
        else:
            self.create_empty_state(
                self.downloads_container,
                icon_code="f090",
                title="No Active Downloads",
                description="Your download queue is empty. Paste a video URL on the home page to start downloading."
            )
        


        # --- Footer ---
        footer = ctk.CTkFrame(layout, fg_color="transparent")
        footer.pack(fill="x", pady=40)
        ctk.CTkFrame(footer, height=1, fg_color=self.border_color).pack(fill="x", pady=(0, 20))
        
        foot_row = ctk.CTkFrame(footer, fg_color="transparent")
        foot_row.pack(fill="x")
        ctk.CTkLabel(foot_row, text="Storage: 124GB Free of 500GB", font=self.font_small, text_color=self.text_secondary).pack(side="left")
        ctk.CTkLabel(foot_row, text=f"VidFetch v{__version__}", font=self.font_small, text_color=self.text_secondary).pack(side="right")

    def create_download_card(self, parent, data):
        """Create a styled download card"""
        is_completed = data.get("status") == "completed"
        
        # Theme-aware colors
        border_col = self.col_success if is_completed else self.border_color
        
        # Outer Card
        card = ctk.CTkFrame(parent, fg_color=self.card_color, corner_radius=12, border_width=1, border_color=border_col)
        card.pack(fill="x", pady=8)
        
        # Inner Content Wrapper
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=4, pady=4)
        
        # --- 1. Thumbnail ---
        thumb_box = ctk.CTkFrame(inner, fg_color="transparent", width=144, height=81)
        thumb_box.pack(side="left", padx=(12, 16), pady=12)
        thumb_box.pack_propagate(False)
        
        # Thumbnail Content
        thumb = ctk.CTkFrame(thumb_box, fg_color=data.get("bg_color", "#333"), corner_radius=8)
        thumb.pack(fill="both", expand=True)
        
        if "format" in data:
            ctk.CTkLabel(thumb, text=data["format"], font=("Helvetica", 10, "bold"), 
                        fg_color="#000000", text_color="white", corner_radius=4).place(relx=0.96, rely=0.94, anchor="se")
            
        if is_completed:
            check_icon = self.get_icon_image("e876", (14, 14))
            if check_icon:
                check_label = ctk.CTkLabel(thumb, text="", image=check_icon,
                                          fg_color="#22c55e", width=20, height=20, corner_radius=10)
                check_label.place(relx=0.96, rely=0.06, anchor="ne")
            
        if data.get("status") != "completed" and data.get("is_playlist"):
            playlist_icon = self.get_icon_image("e05f", (14, 14))
            if playlist_icon:
                playlist_label = ctk.CTkLabel(thumb, text="", image=playlist_icon,
                                            fg_color="#000000", width=24, height=20, corner_radius=4)
                playlist_label.place(relx=0.04, rely=0.06, anchor="nw")

        # --- 2. Actions (placed on right) ---
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(side="right", padx=(0, 16), fill="y")
        
        ctk.CTkFrame(actions, width=1, fg_color=self.border_color, height=40).pack(side="left", fill="y", padx=(0, 16), pady=20)
        
        if is_completed:
            folder_icon = self.get_icon_image("e2c8", (20, 20))
            play_icon = self.get_icon_image("e037", (20, 20))
            ctk.CTkButton(actions, text="", image=folder_icon, width=40, height=40,
                         fg_color="transparent", hover_color="#14532d", cursor="hand2").pack(side="left", padx=4)
            ctk.CTkButton(actions, text="", image=play_icon, width=40, height=40,
                         fg_color="transparent", hover_color=self.col_primary, cursor="hand2").pack(side="left", padx=4)
        else:
            pause_icon = self.get_icon_image("e034", (20, 20))
            close_icon = self.get_icon_image("e5cd", (20, 20))
            ctk.CTkButton(actions, text="", image=pause_icon, width=40, height=40,
                         fg_color="transparent", hover_color=self.col_primary, cursor="hand2").pack(side="left", padx=4)
            ctk.CTkButton(actions, text="", image=close_icon, width=40, height=40,
                         fg_color="transparent", hover_color="#7f1d1d", cursor="hand2").pack(side="left", padx=4)

        # --- 3. Info ---
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=12)
        
        row1 = ctk.CTkFrame(info, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 4))
        
        ctk.CTkLabel(row1, text=data["title"], font=self.font_h2, text_color=self.text_main).pack(side="left", padx=(0, 12))
        
        if "tags" in data:
            for tag in data["tags"]:
                is_success = tag == "Completed"
                tag_bg = "#14532d" if is_success else self.bg_color
                tag_fg = "#4ade80" if is_success else self.text_secondary
                ctk.CTkLabel(row1, text=tag, font=("Helvetica", 10, "bold"), fg_color=tag_bg, 
                            text_color=tag_fg, corner_radius=6, padx=8, pady=2).pack(side="left", padx=4)

        if "subtitle" in data:
             ctk.CTkLabel(row1, text=data["subtitle"], font=self.font_small, text_color=self.text_secondary).pack(side="left", padx=8)

        row2 = ctk.CTkFrame(info, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 0))
        
        meta_top = ctk.CTkFrame(row2, fg_color="transparent")
        meta_top.pack(fill="x", pady=(0, 4))
        
        prog = data.get("progress", 0)
        col = self.col_primary if not is_completed else self.col_success
        ctk.CTkLabel(meta_top, text=f"{int(prog*100)}%", font=("Helvetica", 12, "bold"), text_color=col).pack(side="left")
        
        stats = ctk.CTkFrame(meta_top, fg_color="transparent")
        stats.pack(side="right")
        
        # Stats Icons/Text
        s_icon_code = "e1db" if is_completed else "f090"
        s_val = data.get("size") if is_completed else data.get("speed")
        t_icon_code = "e916" if is_completed else "e8b5"
        t_val = data.get("date") if is_completed else data.get("left")
        
        if s_val:
            s_icon_img = self.get_icon_image(s_icon_code, (14, 14))
            if s_icon_img:
                ctk.CTkLabel(stats, text="", image=s_icon_img).pack(side="left", padx=(0,4))
            ctk.CTkLabel(stats, text=s_val, font=self.font_small, text_color=self.text_secondary).pack(side="left", padx=(0,12))
        if t_val:
            t_icon_img = self.get_icon_image(t_icon_code, (14, 14))
            if t_icon_img:
                ctk.CTkLabel(stats, text="", image=t_icon_img).pack(side="left", padx=(0,4))
            ctk.CTkLabel(stats, text=t_val, font=self.font_small, text_color=self.text_secondary).pack(side="left")

        progress_bar = ctk.CTkProgressBar(row2, height=6, corner_radius=3, progress_color=col, fg_color=self.border_color)
        progress_bar.pack(fill="x")
        progress_bar.set(prog)

    def show_view(self, view_name: str):
        """Show a specific view."""
        self.current_view = view_name
        
        if view_name == "home":
            self.clear_content()
            self.create_main_content()
        elif view_name == "results":
            # Results view is created dynamically in show_single/show_playlist
            pass
        elif view_name == "downloads":
            self.show_downloads_view()
            self.update_downloads_display()

    def on_format_change(self, format_type: str):
        """Handle format toggle change."""
        self.format_mode = format_type

    def paste_from_clipboard(self):
        """Paste from clipboard (alias for paste_clip for compatibility)."""
        self.paste_clip()
    
    def create_footer(self):
        """Create footer"""
        f = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="transparent")
        f.grid(row=2, column=0, sticky="ew")
        f.pack_propagate(False)
        
        ctk.CTkLabel(f, text="© 2024 VidFetch. All rights reserved.", 
                    font=self.font_small, text_color=self.text_secondary).pack(side="left", padx=40, pady=6)
        
        link_box = ctk.CTkFrame(f, fg_color="transparent")
        link_box.pack(side="right", padx=40, pady=6)
        for t in ["Terms of Service", "Privacy Policy", "Support"]:
            ctk.CTkButton(link_box, text=t, fg_color="transparent", 
                         text_color=self.text_secondary, width=120, height=28,
                         font=self.font_small, hover_color=self.card_color).pack(side="left", padx=4)

    def fetch_info(self):
        """Fetch video/playlist information."""
        url = self.url_var.get().strip()
        if not url or url == "Paste YouTube link here...":
            return
        
        # Disable input
        self.url_entry.configure(state='disabled')
        
        # Show loading
        self.show_loading()
        
        # Fetch in background
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def show_loading(self):
        """Show loading overlay."""
        # Check if overlay exists and is valid
        if hasattr(self, 'loading_overlay'):
            try:
                if not self.loading_overlay.winfo_exists():
                    delattr(self, 'loading_overlay')
            except:
                delattr(self, 'loading_overlay')
        
        if not hasattr(self, 'loading_overlay'):
            # Create on self (main window) instead of main_view which gets cleared
            self.loading_overlay = ctk.CTkFrame(self, fg_color=self.bg_color, corner_radius=16)
            
            spinner = ctk.CTkLabel(
                self.loading_overlay, text="⏳",
                font=("Helvetica", 48), text_color=self.text_main
            )
            spinner.pack(pady=20)
            
            loading_text = ctk.CTkLabel(
                self.loading_overlay, text="Analyzing URL...", font=self.font_h2, text_color=self.text_main
            )
            loading_text.pack(pady=(0, 20))
        
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor='center')
        self.loading_overlay.lift()

    def hide_loading(self):
        """Hide loading overlay."""
        if hasattr(self, 'loading_overlay') and self.loading_overlay.winfo_exists():
            try:
                self.loading_overlay.place_forget()
            except:
                pass

    def _fetch_worker(self, url: str):
        """Worker thread for fetching metadata."""
        try:
            metadata = self.youtube.get_video_info(url)
            self.after(0, lambda: self.handle_fetch_result(metadata))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            # Safely re-enable URL entry if it still exists
            def safe_enable():
                if hasattr(self, 'url_entry') and self.url_entry.winfo_exists():
                    try:
                        self.url_entry.configure(state='normal')
                    except:
                        pass
            self.after(0, safe_enable)
            self.after(0, self.hide_loading)

    def handle_fetch_result(self, result):
        """Handle the result of metadata fetch."""
        if isinstance(result, PlaylistMetadata):
            self.current_playlist = result
            self.show_playlist(result)
        else:
            self.current_metadata = result
            self.show_single(result)
        
        # Results view is created in show_single/show_playlist, no need to call show_view

    def show_single(self, meta: VideoMetadata):
        """Show single video information with new design."""
        self.clear_content()
        self.current_metadata = meta
        
        # Web Container: Centered, fixed width layout
        content = ctk.CTkFrame(self.main_view, fg_color="transparent", width=1000)
        content.grid(row=0, column=0, pady=40, padx=20)
        content.grid_columnconfigure(0, weight=1)

        # 1. Search Bar (Full Width)
        search_row = ctk.CTkFrame(content, fg_color="transparent", width=1000)
        search_row.pack(fill="x", pady=(0, 30))
        
        # Input Container
        input_container = ctk.CTkFrame(search_row, fg_color="transparent")
        input_container.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        input_bg = ctk.CTkFrame(input_container, fg_color=self.header_color, 
                                border_width=1, border_color=self.border_color,
                                corner_radius=12, height=54)
        input_bg.pack(fill="x")
        input_bg.pack_propagate(False)
        
        # Link icon
        link_icon_search = self.get_icon_image("e157", (18, 18))
        if link_icon_search:
            ctk.CTkLabel(input_bg, text="", image=link_icon_search).pack(side="left", padx=15)
        else:
            ctk.CTkLabel(input_bg, text="🔗", font=self.font_body, text_color=self.text_secondary).pack(side="left", padx=15)
        
        search_entry = ctk.CTkEntry(input_bg, placeholder_text="Paste another video link...", 
                                      border_width=0, fg_color="transparent", font=self.font_body)
        search_entry.pack(side="left", expand=True, fill="both", pady=2)
        search_entry.insert(0, meta.original_url)
        search_entry.bind('<Return>', lambda e: self._search_from_entry(search_entry.get()))
        
        # Paste Button
        paste_icon_search = self.get_icon_image("e14f", (18, 18))
        if paste_icon_search:
            def paste_search():
                try:
                    clipboard_text = self.clipboard_get()
                    if clipboard_text:
                        search_entry.delete(0, 'end')
                        search_entry.insert(0, clipboard_text)
                except Exception as e:
                    pass
            
            ctk.CTkButton(input_bg, text="", image=paste_icon_search, width=32, height=32,
                         corner_radius=8, fg_color="transparent",
                         hover_color=self.border_color, command=paste_search).pack(side="right", padx=8)

        # Search Button
        search_icon = self.get_icon_image("e8b6", (20, 20))
        ctk.CTkButton(search_row, text="Search", font=self.font_h2, 
                      height=56, width=140, fg_color=self.accent_blue, 
                      hover_color="#0d6bc4", corner_radius=12,
                      image=search_icon, compound="left",
                      command=lambda: self._search_from_entry(search_entry.get())).pack(side="right")

        # 2. Results Header
        header_row = ctk.CTkFrame(content, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(header_row, text="Search Results", font=self.font_h2, text_color=self.text_main).pack(side="left")
        
        status = ctk.CTkFrame(header_row, fg_color="transparent")
        status.pack(side="right")
        check_icon_status = self.get_icon_image("e876", (16, 16))
        if check_icon_status:
            ctk.CTkLabel(status, text="", image=check_icon_status).pack(side="left", padx=5)
        ctk.CTkLabel(status, text="Ready to download", font=self.font_small, text_color=self.text_secondary).pack(side="left")

        # 3. Main Video Card
        self.create_video_card(content, meta)
        
        # 4. Playlist Section (if applicable - not shown for single videos)
        # self.create_playlist_section(content)
    
    def create_video_card(self, parent, meta: VideoMetadata):
        """Create video card with new design"""
        card = ctk.CTkFrame(parent, fg_color=self.card_color, corner_radius=16, 
                           border_width=1, border_color=self.border_color)
        card.pack(fill="x", pady=(0, 40))
        
        # Grid layout
        card.grid_columnconfigure(0, weight=0)  # Fixed width for thumbnail
        card.grid_columnconfigure(1, weight=1)  # Info side stretches
        
        # --- LEFT COLUMN: Thumbnail & Channel ---
        left_col = ctk.CTkFrame(card, fg_color="transparent")
        left_col.grid(row=0, column=0, padx=24, pady=24, sticky="n")
        
        # Thumbnail Container - 16:9 Aspect Ratio (320x180)
        thumb_width, thumb_height = 320, 180
        thumb_frame = ctk.CTkFrame(left_col, width=thumb_width, height=thumb_height, 
                                   fg_color="#1f2937", corner_radius=12)
        thumb_frame.pack(pady=(0, 16))
        thumb_frame.pack_propagate(False)
        
        # Thumbnail label
        self.result_thumb = ctk.CTkLabel(thumb_frame, fg_color="#1f2937", 
                                        anchor='center', text="Loading...",
                                        text_color="white", font=self.font_small)
        self.result_thumb.pack(expand=True, fill='both')
        self.result_thumb.image = None
        
        # Play Button (Icon Button)
        play_icon_large = self.get_icon_image("e039", (64, 64))
        if play_icon_large:
            play_btn = ctk.CTkButton(thumb_frame, text="", image=play_icon_large,
                                 fg_color="transparent", hover_color="#374151",
                                     width=64, height=64)
            play_btn.place(relx=0.5, rely=0.5, anchor="center")
        
        # Duration Badge
        self.create_time_badge(thumb_frame, format_duration(meta.duration)).place(relx=0.96, rely=0.94, anchor="se")

        # Channel Row (simplified - no channel info in metadata)
        chan_row = ctk.CTkFrame(left_col, fg_color="transparent")
        chan_row.pack(fill="x")
        
        # Avatar
        avatar = ctk.CTkLabel(chan_row, text="Y", font=self.font_h2, width=40, height=40,
                             fg_color=self.border_color, text_color=self.accent_blue, corner_radius=20)
        avatar.pack(side="left")
        
        # Channel Details
        chan_info = ctk.CTkFrame(chan_row, fg_color="transparent")
        chan_info.pack(side="left", padx=12)
        ctk.CTkLabel(chan_info, text="YouTube", font=self.font_body, text_color=self.text_main).pack(anchor="w")
        ctk.CTkLabel(chan_info, text="Video", font=self.font_caps, text_color=self.text_secondary).pack(anchor="w")
        
        # --- RIGHT COLUMN: Info & Actions ---
        right_col = ctk.CTkFrame(card, fg_color="transparent")
        right_col.grid(row=0, column=1, padx=24, pady=24, sticky="nsew")
        
        # Title
        ctk.CTkLabel(right_col, text=meta.title, 
                    font=self.font_h2, text_color=self.text_main, wraplength=500, justify="left").pack(anchor="w", pady=(0, 8))
        
        # Metadata
        meta_row = ctk.CTkFrame(right_col, fg_color="transparent")
        meta_row.pack(anchor="w", pady=(0, 24))
        ctk.CTkLabel(meta_row, text=f"Duration: {format_duration(meta.duration)}", font=self.font_small, text_color=self.text_secondary).pack(side="left", padx=(0,10))
        ctk.CTkLabel(meta_row, text="•", font=self.font_small, text_color=self.text_secondary).pack(side="left", padx=(0,10))
        ctk.CTkLabel(meta_row, text="YouTube", font=self.font_small, text_color=self.text_secondary).pack(side="left")

        # Quality Selector
        ctk.CTkLabel(right_col, text="Select Quality", font=self.font_caps, text_color=self.text_secondary).pack(anchor="w", pady=(0, 8))
        
        # Build quality options
        quality_options = []
        self.quality_map = {}
        self.quality_var = ctk.StringVar()
        
        for fmt in sorted(meta.formats, key=lambda f: (f.resolution if f.resolution != 'N/A' else '0x0'), reverse=True):
            if fmt.vcodec == 'none' or fmt.resolution == 'N/A' or not fmt.url:
                continue
            
            filesize_mb = (fmt.filesize / (1024*1024)) if fmt.filesize and fmt.filesize > 0 else 0.0
            size_text = f"{filesize_mb:.1f} MB" if filesize_mb > 0 else "Unknown"
            
            # Extract resolution text
            res_text = fmt.note if fmt.note and fmt.note != 'N/A' else fmt.resolution
            if 'x' in res_text:
                parts = res_text.split('x')
                if len(parts) == 2:
                    res_text = f"{parts[1]}p"
            elif res_text and not res_text.endswith('p'):
                res_text = f"{res_text}p"
            
            label = f"{res_text} • {size_text} • {fmt.ext.upper()}"
            self.quality_map[label] = fmt
            quality_options.append(label)
        
        if quality_options:
            self.quality_var.set(quality_options[0])
            quality_menu = ctk.CTkOptionMenu(right_col, values=quality_options,
                                            variable=self.quality_var,
                                            font=self.font_body, 
                                            fg_color=self.bg_color, button_color=self.bg_color,
                                            button_hover_color=self.border_color,
                                            text_color=self.text_main,
                                            height=48, anchor="w", corner_radius=12)
            quality_menu.pack(fill="x", pady=(0, 40))
        
        # Download Button
        dl_btn = ctk.CTkButton(right_col, text="Download Video", font=self.font_h2, 
                              height=56, fg_color=self.accent_blue, hover_color="#0d6bc4", 
                              corner_radius=12, image=self.download_icon, compound="left",
                              command=self.add_single)
        dl_btn.pack(fill="x")
        
        ctk.CTkLabel(right_col, text="By downloading you agree to our Terms of Service", 
                    font=self.font_caps, text_color=self.text_secondary).pack(pady=(12, 0))
        
        # Load thumbnail
        threading.Thread(target=self._load_result_thumb, args=(meta.thumbnail_url,), daemon=True).start()
    
    def create_time_badge(self, parent, text):
        """Create YouTube-style time badge"""
        badge = ctk.CTkFrame(parent, fg_color="black", corner_radius=6)
        ctk.CTkLabel(badge, text=text, font=self.font_caps, text_color="white").pack(padx=6, pady=2)
        return badge
    
    def _search_from_entry(self, url: str):
        """Handle search from the results page search bar."""
        if url and url.strip():
            self.url_var.set(url.strip())
            self.fetch_info()

    def show_playlist(self, playlist: PlaylistMetadata):
        """Show playlist information with new design matching the image."""
        self.clear_content()
        self.current_playlist = playlist
        
        # Container
        container = ctk.CTkFrame(self.main_view, fg_color="transparent", width=1000)
        container.grid(row=0, column=0, pady=40, padx=20)
        container.grid_columnconfigure(0, weight=1)
        
        # Header with title
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill='x', pady=(0, 24))
        
        ctk.CTkLabel(
            header, text=f"{playlist.title} ({len(playlist.entries)} videos)",
            font=self.font_h1, text_color=self.text_main
        ).pack(anchor='w')
        
        # Playlist items in a card
        list_card = ctk.CTkFrame(container, fg_color=self.card_color, corner_radius=16,
                                border_width=1, border_color=self.border_color)
        list_card.pack(fill='both', expand=True, pady=(0, 24))
        
        # Scrollable frame for playlist items
        list_frame = ctk.CTkScrollableFrame(list_card, fg_color="transparent")
        list_frame.pack(fill='both', expand=True, padx=16, pady=16)
        
        self.pl_vars = []
        for i, entry in enumerate(playlist.entries):
            var = tk.BooleanVar(value=True)
            self.pl_vars.append((entry, var))
            
            # Row for each playlist item
            row = ctk.CTkFrame(list_frame, fg_color="transparent")
            row.pack(fill='x', pady=4)
            
            # Checkbox
            cb = ctk.CTkCheckBox(
                row, text="", variable=var, width=20, height=20
            )
            cb.pack(side='left', padx=(0, 12))
            
            # Title
            title_label = ctk.CTkLabel(
                row, text=f"{i+1}. {entry.title}", 
                font=self.font_body, text_color=self.text_main,
                anchor='w'
            )
            title_label.pack(side='left', fill='x', expand=True, padx=(0, 12))
            
            # Duration
            duration_label = ctk.CTkLabel(
                row, text=format_duration(entry.duration), 
                font=self.font_small, text_color=self.text_secondary
            )
            duration_label.pack(side='right')
        
        # Download button at bottom
        download_btn = ctk.CTkButton(
            container, text="Download Selected", command=self.process_playlist,
            font=self.font_h2, fg_color=self.accent_blue, hover_color="#0d6bc4",
            height=56, corner_radius=12
        )
        download_btn.pack(pady=(0, 16))

    def _load_result_thumb(self, url: str):
        """Load result thumbnail."""
        try:
            import logging
            logging.info(f"Loading thumbnail from: {url}")
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            
            pil_img = Image.open(BytesIO(resp.content))
            # Resize to fit container (320x180 for video card)
            thumb_width, thumb_height = 320, 180
            pil_img = pil_img.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            
            # Use CTkImage for CustomTkinter
            ctk_img = CTkImage(light_image=pil_img, dark_image=pil_img, size=(thumb_width, thumb_height))
            
            # Update UI in main thread
            def update_thumb(img=ctk_img):
                try:
                    if hasattr(self, 'result_thumb') and self.result_thumb.winfo_exists():
                        self.result_thumb.configure(image=img, text="")
                        self.result_thumb.image = img
                        logging.info(f"Thumbnail loaded successfully: {thumb_width}x{thumb_height}")
                except Exception as e:
                    logging.error(f"Error updating thumbnail: {e}", exc_info=True)
            
            self.after(0, update_thumb)
        except Exception as e:
            import logging
            logging.error(f"Error loading thumbnail: {e}", exc_info=True)
            # Show placeholder on error
            def show_error():
                if hasattr(self, 'result_thumb') and self.result_thumb.winfo_exists():
                    self.result_thumb.configure(
                        text="📹\nNo thumbnail", 
                        text_color="white", 
                        font=self.font_body
                    )
            self.after(0, show_error)

    def add_single(self):
        """Add single video to download queue."""
        try:
            if not self.current_metadata:
                return
            
            # Check if quality_var and quality_map exist (created in show_single)
            if not hasattr(self, 'quality_var') or not hasattr(self, 'quality_map'):
                return
            
            val = self.quality_var.get()
            
            if not val:
                return
            
            fmt = self.quality_map.get(val)
            if not fmt:
                return
            
            # Check if format has URL
            if not fmt.url:
                messagebox.showerror("Error", "Selected format is not available for download.")
                return
            
            target_ext = 'm4a' if fmt.ext == 'mp4' else 'webm'
            
            # Find best audio (only if format is video-only)
            best_audio = None
            if fmt.is_video_only:
                audios = [f for f in self.current_metadata.formats if f.acodec != 'none' and f.vcodec == 'none' and f.url]
                
                def audio_score(f):
                    lang = (f.language or "").lower()
                    is_english = "en" in lang or "eng" in lang
                    lang_score = 2 if is_english else (1 if not lang else 0)
                    return (lang_score, f.filesize or 0)
                
                audios.sort(key=audio_score, reverse=True)
                best_audio = next((f for f in audios if f.ext == target_ext), None) or (audios[0] if audios else None)
            
            safe_title = "".join([c for c in self.current_metadata.title if c.isalnum() or c in (' ', '-', '_')]).strip()
            filename = f"{safe_title}_{fmt.resolution}.{fmt.ext}"
            save_path = self.config.download_path / filename
            
            # Create DownloadTask
            task = DownloadTask(
                self.current_metadata.title, fmt.url,
                best_audio.url if best_audio else None, save_path,
                thumb_url=self.current_metadata.thumbnail_url,
                headers=fmt.http_headers
            )
            self.download_tasks.append(task)
            task.start()
            
            # Switch to downloads view to show the item
            self.show_view("downloads")
        except Exception as e:
            import logging
            logging.error(f"Error adding download: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to add download: {str(e)}")

    def process_playlist(self):
        """Process selected playlist items."""
        if not self.current_playlist:
            return
        
        selected = [e for e, v in self.pl_vars if v.get()]
        if not selected:
            return
        
        # Use "Best Available" for now
        threading.Thread(target=self._batch_worker, args=(selected, "Best Available"), daemon=True).start()
        self.show_view("downloads")

    def _batch_worker(self, entries: list[PlaylistEntry], pref: str):
        """Worker thread for batch processing."""
        for entry in entries:
            try:
                meta = self.youtube.get_video_info(entry.url)
                if isinstance(meta, VideoMetadata):
                    self.after(0, lambda m=meta: self._auto_add(m, pref))
            except Exception:
                pass

    def _auto_add(self, meta: VideoMetadata, pref: str):
        """Automatically add video to queue."""
        # Simplified version - find best format
        best = next((f for f in meta.formats if f.is_video_only and f.ext == 'mp4'), None)
        if not best:
            return
        
        target_ext = 'm4a' if best.ext == 'mp4' else 'webm'
        audios = [f for f in meta.formats if f.acodec != 'none' and f.vcodec == 'none']
        
        def audio_score(f):
            lang = (f.language or "").lower()
            is_english = "en" in lang or "eng" in lang
            lang_score = 2 if is_english else (1 if not lang else 0)
            return (lang_score, f.filesize)
        
        audios.sort(key=audio_score, reverse=True)
        best_audio = next((f for f in audios if f.ext == target_ext), None) or (audios[0] if audios else None)
        
        fname = f"{meta.title}_{best.resolution}.mp4"
        fname = "".join([c for c in fname if c.isalnum() or c in (' ', '-', '_', '.')])
        save_path = self.config.download_path / fname
        
        # Create DownloadTask
        task = DownloadTask(
             meta.title, best.url,
             best_audio.url if best_audio else None, save_path,
             thumb_url=meta.thumbnail_url, headers=best.http_headers
        )
        self.download_tasks.append(task)
        task.start()
        
        # Switch to downloads view is handled by caller usually or implicit?
        # In process_playlist, we call show_view("downloads") after starting batch.
        # But _auto_add is called via after() from thread. So we should switch if it's the first one?
        # Actually existing code called show_view("downloads") in process_playlist, not _auto_add.
        # But _auto_add had lines to switch.
        
        # Switch to downloads view
        self.show_view("downloads")

    def update_downloads_display(self):
        """Update downloads count display."""
        # This is now handled by view reconstruction or can be used for sidebar count
        pass

    def pause_all_downloads(self):
        """Pause all active downloads."""
        for task in self.download_tasks:
            if not task.is_paused:
                task.toggle_pause()
                
        # Refresh view if visible
        if self.current_view == "downloads":
            pass # tasks auto-update widgets via observers

    def resume_all_downloads(self):
        """Resume all paused downloads."""
        for task in self.download_tasks:
            if task.is_paused:
                task.toggle_pause()
