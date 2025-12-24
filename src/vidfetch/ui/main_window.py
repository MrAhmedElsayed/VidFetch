"""Main application window."""

import threading
import customtkinter as ctk
import tkinter as tk  # Still needed for some widgets like Canvas
from tkinter import messagebox, filedialog, ttk
from pathlib import Path
from typing import Optional
from io import BytesIO
import requests
from PIL import Image, ImageTk

from ..core import YouTubeClient, VideoMetadata, PlaylistMetadata, PlaylistEntry
from ..utils import Config, resource_path
from ..version import __version__
from .download_item import DownloadItem
from .components import COLORS

# Configure CustomTkinter theme to match HTML design
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Custom color theme matching HTML design
COLORS = {
    "primary": "#137fec",
    "primary_hover": "#2563eb",
    "background_dark": "#101922",
    "surface_dark": "#1e293b",
    "surface_light": "#ffffff",
    "text_primary": "#f1f5f9",
    "text_secondary": "#92adc9",
    "border": "#233648",
    "input_bg": "#111a22",
    "input_border": "#324d67",
    "header_bg": "#111a22",
    "card": "#192633",
}


def format_duration(seconds: int) -> str:
    """Format duration like YouTube (MM:SS or HH:MM:SS)."""
    if seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"


class VidFetchApp(ctk.CTk):
    """Main application window for VidFetch."""
    
    def __init__(self):
        super().__init__()
        try:
            self.title(f"VidFetch v{__version__}")
            self.geometry("1200x800")
            self.configure(fg_color=COLORS["background_dark"])
        except Exception as e:
            import logging
            logging.error(f"Error in VidFetchApp.__init__: {e}", exc_info=True)
            raise
        
        try:
            icon_path = resource_path("assets/logo.ico")
            if icon_path.exists():
                icon_str = str(icon_path).replace('/', '\\')
                self.iconbitmap(icon_str)
        except Exception:
            pass
        
        try:
            import ctypes
            if hasattr(ctypes, 'windll'):
                myappid = f"com.vidfetch.app.{__version__}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # Data
        self.current_metadata: Optional[VideoMetadata] = None
        self.current_playlist: Optional[PlaylistMetadata] = None
        self.youtube = YouTubeClient()
        self.config = Config()
        self.current_view = "home"
        self.format_mode = "video"  # "video" or "audio"
        self.download_items = []  # Track download items for downloads view
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_container = ctk.CTkFrame(self, fg_color=COLORS["background_dark"])
        main_container.pack(fill='both', expand=True)
        
        # Header
        self.setup_header(main_container)
        
        # Content area (views)
        self.content_area = ctk.CTkFrame(main_container, fg_color=COLORS["background_dark"])
        self.content_area.pack(fill='both', expand=True)
        
        # Initialize views
        self.setup_home_view()
        self.setup_downloads_view()
        
        # Settings modal (initially hidden)
        self.setup_settings_modal()
        
        # Show home view by default
        self.show_view("home")

    def setup_header(self, parent):
        """Setup the global header."""
        header = ctk.CTkFrame(parent, height=64, fg_color=COLORS["header_bg"], corner_radius=0)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        # Inner container with max-width 1200px equivalent
        inner = ctk.CTkFrame(header, fg_color=COLORS["header_bg"], corner_radius=0)
        inner.pack(fill='both', expand=True, padx=24, pady=12)
        
        # Logo and title
        logo_frame = ctk.CTkFrame(inner, fg_color=COLORS["header_bg"], corner_radius=0)
        logo_frame.pack(side='left')
        
        # Logo icon container (size-8 rounded-lg bg-primary/10)
        icon_container = ctk.CTkFrame(
            logo_frame, width=32, height=32,
            fg_color=COLORS["primary"], corner_radius=8
        )
        icon_container.pack(side='left', padx=(0, 12))
        
        # Logo icon (download symbol)
        logo_icon = ctk.CTkLabel(
            icon_container, text="⬇",
            text_color="white",
            font=("Segoe UI", 16)
        )
        logo_icon.place(relx=0.5, rely=0.5, anchor='center')
        
        title = ctk.CTkLabel(
            logo_frame, text="VidFetch",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(side='left')
        
        # Navigation (right side)
        nav_frame = ctk.CTkFrame(inner, fg_color=COLORS["header_bg"], corner_radius=0)
        nav_frame.pack(side='right')
        
        home_btn = ctk.CTkButton(
            nav_frame, text="Home",
            command=lambda: self.show_view("home"),
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["header_bg"],
            font=("Segoe UI", 11)
        )
        home_btn.pack(side='left', padx=8)
        
        downloads_btn = ctk.CTkButton(
            nav_frame, text="Downloads",
            command=lambda: self.show_view("downloads"),
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["header_bg"],
            font=("Segoe UI", 11)
        )
        downloads_btn.pack(side='left', padx=8)
        
        settings_btn = ctk.CTkButton(
            nav_frame, text="⚙", command=self.open_settings,
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["header_bg"],
            width=32, height=32
        )
        settings_btn.pack(side='left', padx=8)

    def setup_home_view(self):
        """Setup the home view."""
        home_view = ctk.CTkFrame(self.content_area, fg_color=COLORS["background_dark"], corner_radius=0)
        home_view.pack(fill='both', expand=True)
        
        # Centered container
        center_frame = ctk.CTkFrame(home_view, fg_color="transparent", corner_radius=0)
        center_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Hero heading
        hero_frame = ctk.CTkFrame(center_frame, fg_color="transparent", corner_radius=0)
        hero_frame.pack(pady=(0, 40))
        
        # Title with accent color on "Downloader" - text-4xl md:text-6xl font-black tracking-tight leading-[1.1]
        title_frame = ctk.CTkFrame(hero_frame, fg_color="transparent", corner_radius=0)
        title_frame.pack()
        
        ctk.CTkLabel(
            title_frame, text="Video ",
            font=("Segoe UI", 60, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side='left')
        
        ctk.CTkLabel(
            title_frame, text="Downloader",
            font=("Segoe UI", 60, "bold"),
            text_color=COLORS["primary"]
        ).pack(side='left')
        
        hero_subtitle = ctk.CTkLabel(
            hero_frame, 
            text="Download videos and playlists in 4K, HD, or MP3 audio instantly. No registration required.",
            font=("Segoe UI", 16),
            text_color=COLORS["text_secondary"],
            wraplength=700
        )
        hero_subtitle.pack(pady=(16, 0))
        
        # Main input card
        card = ctk.CTkFrame(center_frame, fg_color=COLORS["card"], corner_radius=16)
        card.pack(pady=20, padx=20)
        
        # Format toggles
        format_frame = ctk.CTkFrame(card, fg_color=COLORS["border"], corner_radius=12)
        format_frame.pack(pady=(24, 24), padx=24)
        
        self.format_var = ctk.StringVar(value="video")
        self.format_var.trace('w', lambda *args: self.on_format_change(self.format_var.get()))
        
        video_btn = ctk.CTkRadioButton(
            format_frame, text="MP4 Video", variable=self.format_var, value="video",
            font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["primary"],
            text_color=COLORS["text_secondary"]
        )
        video_btn.pack(side='left', padx=8, pady=8)
        
        audio_btn = ctk.CTkRadioButton(
            format_frame, text="MP3 Audio", variable=self.format_var, value="audio",
            font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["primary"],
            text_color=COLORS["text_secondary"]
        )
        audio_btn.pack(side='left', padx=8, pady=8)
        
        # Input area
        input_frame = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        input_frame.pack(fill='x', pady=(0, 16), padx=24)
        
        self.url_var = ctk.StringVar()
        # Input with icon inside
        input_container = ctk.CTkFrame(input_frame, fg_color=COLORS["input_bg"], corner_radius=12, border_width=1, border_color=COLORS["input_border"])
        input_container.pack(side='left', fill='x', expand=True, padx=(0, 16))
        
        # Link icon on left
        icon_label = ctk.CTkLabel(
            input_container, text="[LINK]",
            font=("Segoe UI", 10),
            text_color=COLORS["text_secondary"]
        )
        icon_label.pack(side='left', padx=16)
        
        self.url_entry = ctk.CTkEntry(
            input_container, textvariable=self.url_var,
            placeholder_text="Paste YouTube link here...",
            font=("Segoe UI", 12),
            fg_color=COLORS["input_bg"],
            border_width=0,
            height=56
        )
        self.url_entry.pack(side='left', fill='x', expand=True, padx=8)
        self.url_entry.bind('<Return>', lambda e: self.fetch_info())
        
        paste_btn = ctk.CTkButton(
            input_container, text="Paste", command=self.paste_from_clipboard,
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["input_bg"],
            font=("Segoe UI", 9),
            width=60
        )
        paste_btn.pack(side='right', padx=8)
        
        get_video_btn = ctk.CTkButton(
            input_frame, text="Get Video", command=self.fetch_info,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=("Segoe UI", 12, "bold"),
            height=56,
            corner_radius=12
        )
        get_video_btn.pack(side='left')
        
        # Features
        features_frame = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        features_frame.pack(pady=(0, 24), padx=24)
        
        features = [
            ("✓", "Unlimited Downloads"),
            ("✓", "High Speed Converter"),
            ("✓", "No Registration")
        ]
        
        # Features
        for icon, text in features:
            feat_frame = ctk.CTkFrame(features_frame, fg_color="transparent", corner_radius=0)
            feat_frame.pack(side='left', padx=16)
            
            ctk.CTkLabel(
                feat_frame, text="✓",
                font=("Segoe UI", 16),
                text_color="#22c55e"
            ).pack(side='left', padx=(0, 6))
            
            ctk.CTkLabel(
                feat_frame, text=text,
                font=("Segoe UI", 10),
                text_color=COLORS["text_secondary"]
            ).pack(side='left')
        
        # Store reference
        self.home_view = home_view
        
        # Results view (initially hidden)
        self.results_view = None

    def setup_downloads_view(self):
        """Setup the downloads view."""
        downloads_view = ctk.CTkFrame(self.content_area, fg_color=COLORS["background_dark"], corner_radius=0)
        
        # Container - max-w-[1200px] mx-auto px-6 py-8
        container = ctk.CTkFrame(downloads_view, fg_color="transparent", corner_radius=0)
        container.pack(fill='both', expand=True)
        
        # Main content with gap-8
        content_frame = ctk.CTkFrame(container, fg_color="transparent", corner_radius=0)
        content_frame.pack(fill='both', expand=True)
        
        # Page Header & Actions - flex flex-col md:flex-row md:items-end justify-between gap-6
        header_frame = ctk.CTkFrame(content_frame, fg_color="transparent", corner_radius=0)
        header_frame.pack(fill='x', pady=(0, 32))
        
        # Left side - flex flex-col gap-2
        title_section = ctk.CTkFrame(header_frame, fg_color="transparent", corner_radius=0)
        title_section.pack(side='left', anchor='sw')
        
        # Title - text-3xl md:text-4xl font-bold tracking-tight
        title_row = ctk.CTkFrame(title_section, fg_color="transparent", corner_radius=0)
        title_row.pack(anchor='w')
        
        title = ctk.CTkLabel(
            title_row, text="Active Downloads",
            font=("Segoe UI", 36, "bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(side='left')
        
        count_label = ctk.CTkLabel(
            title_row, text="(0)",
            font=("Segoe UI", 36, "bold"),
            text_color=COLORS["text_secondary"]
        )
        count_label.pack(side='left', padx=(8, 0))
        self.downloads_count_label = count_label
        
        # Subtitle - text-slate-500 dark:text-[#92adc9] text-base
        subtitle = ctk.CTkLabel(
            title_section, text="Monitor progress, manage queue, and control speed.",
            font=("Segoe UI", 14),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(anchor='w', pady=(8, 0))
        
        # Right side - flex items-center gap-3
        actions_frame = ctk.CTkFrame(header_frame, fg_color="transparent", corner_radius=0)
        actions_frame.pack(side='right', anchor='se')
        
        # Pause All button - h-10 px-4 rounded-lg bg-slate-200 dark:bg-[#233648]
        pause_all_btn = ctk.CTkButton(
            actions_frame, text="Pause All",
            command=self.pause_all_downloads,
            fg_color=COLORS["border"],
            hover_color=COLORS["input_border"],
            text_color=COLORS["text_secondary"],
            font=("Segoe UI", 11)
        )
        pause_all_btn.pack(side='left', padx=(0, 12))
        
        # Resume All button
        resume_all_btn = ctk.CTkButton(
            actions_frame, text="Resume All",
            command=self.resume_all_downloads,
            fg_color=COLORS["border"],
            hover_color=COLORS["input_border"],
            text_color=COLORS["text_secondary"],
            font=("Segoe UI", 11)
        )
        resume_all_btn.pack(side='left')
        
        # Downloads Table - rounded-xl border border-slate-200 dark:border-slate-700/50 bg-surface-light dark:bg-[#111a22] shadow-sm
        table_container = ctk.CTkFrame(
            content_frame, fg_color=COLORS["card"], corner_radius=16,
            border_width=1, border_color=COLORS["border"]
        )
        table_container.pack(fill='both', expand=True)
        
        # Table header - bg-slate-50 dark:bg-[#192633] border-b border-slate-200 dark:border-slate-700/50
        header_row = ctk.CTkFrame(table_container, fg_color=COLORS["card"], corner_radius=0)
        header_row.pack(fill='x', side='top')
        
        # Border bottom
        header_border = tk.Frame(header_row, height=1)
        header_border.pack(fill='x', side='bottom')
        
        # Headers - px-6 py-4 text-xs font-semibold uppercase tracking-wider
        headers = [
            ("Preview", 80),
            ("Title & Format", 1),
            ("Progress", 1),
            ("Stats", 120),
            ("Actions", 100)
        ]
        
        for i, (text, weight) in enumerate(headers):
            anchor = 'w' if i == 0 else ('e' if i == len(headers) - 1 else 'w')
            header_cell = ctk.CTkLabel(
                header_row, text=text.upper(),
                font=("Segoe UI", 9, "bold"),
                text_color=COLORS["text_secondary"],
                anchor=anchor
            )
            if weight == 1:
                header_cell.pack(side='left', fill='x', expand=True)
            else:
                header_cell.pack(side='left')
        
        # Scrollable frame for downloads
        downloads_wrapper = ctk.CTkFrame(table_container, fg_color="transparent", corner_radius=0)
        downloads_wrapper.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(downloads_wrapper, highlightthickness=0, bg=COLORS["card"])
        scrollbar = ttk.Scrollbar(downloads_wrapper, orient="vertical", command=canvas.yview)
        self.downloads_container = tk.Frame(canvas, bg=COLORS["card"])
        
        self.downloads_container.bind(
            "<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.downloads_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas.find_all()[0], width=e.width))
        
        self.downloads_view = downloads_view
        self.downloads_canvas = canvas

    def setup_settings_modal(self):
        """Setup the settings modal."""
        self.settings_modal = tk.Toplevel(self)
        self.settings_modal.title("Settings")
        self.settings_modal.geometry("500x300")
        self.settings_modal.configure()
        self.settings_modal.withdraw()  # Hide initially
        self.settings_modal.transient(self)
        # Don't call grab_set() on a withdrawn window - will do it when showing
        
        # Make it modal-like
        self.settings_modal.protocol("WM_DELETE_WINDOW", self.close_settings)
        
        # Header
        header = tk.Frame(self.settings_modal, pady=24, padx=24)
        header.pack(fill='x')
        
        title = tk.Label(
            header, text="Settings", font=("Segoe UI", 20, "bold")
        )
        title.pack(side='left')
        
        close_btn = tk.Button(
            header, text="✕", command=self.close_settings
        )
        close_btn.pack(side='right')
        
        # Content
        content = tk.Frame(self.settings_modal, padx=24, pady=16)
        content.pack(fill='both', expand=True)
        
        # Download path
        path_frame = tk.Frame(content)
        path_frame.pack(fill='x', pady=(0, 16))
        
        tk.Label(
            path_frame, text="Download Path", font=("Segoe UI", 11)
        ).pack(anchor='w', pady=(0, 8))
        
        path_input_frame = tk.Frame(path_frame)
        path_input_frame.pack(fill='x')
        
        self.path_var = tk.StringVar(value=str(self.config.download_path))
        path_entry = tk.Entry(
            path_input_frame, textvariable=self.path_var,
            relief="flat", bd=1,
            highlightthickness=1, font=("Segoe UI", 10)
        )
        path_entry.pack(side='left', fill='x', expand=True, ipady=6, padx=(0, 8))
        
        browse_btn = tk.Button(
            path_input_frame, text="Change", command=self.browse_download_path
        )
        browse_btn.pack(side='left')
        
        # Footer
        footer = tk.Frame(self.settings_modal, pady=16, padx=24)
        footer.pack(fill='x', side='bottom')
        
        save_btn = tk.Button(
            footer, text="Save Changes", command=self.save_settings
        )
        save_btn.pack(side='right')

    def show_view(self, view_name: str):
        """Show a specific view."""
        self.current_view = view_name
        
        # Hide all views
        for widget in self.content_area.winfo_children():
            widget.pack_forget()
        
        if view_name == "home":
            self.home_view.pack(fill='both', expand=True)
        elif view_name == "results":
            if self.results_view:
                self.results_view.pack(fill='both', expand=True)
        elif view_name == "downloads":
            self.downloads_view.pack(fill='both', expand=True)
            self.update_downloads_display()

    def on_format_change(self, format_type: str):
        """Handle format toggle change."""
        self.format_mode = format_type

    def paste_from_clipboard(self):
        """Paste from clipboard."""
        try:
            clipboard_text = self.clipboard_get()
            self.url_var.set(clipboard_text)
            self.url_entry.configure()
        except Exception:
            pass

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
        if not hasattr(self, 'loading_overlay'):
            self.loading_overlay = tk.Frame(
                self.content_area, highlightthickness=2
            )
            self.loading_overlay.place(relx=0.5, rely=0.5, anchor='center')
            
            spinner = tk.Label(
                self.loading_overlay, text="⏳",
                font=("Segoe UI", 48)
            )
            spinner.pack(pady=20)
            
            loading_text = tk.Label(
                self.loading_overlay, text="Analyzing URL...", font=("Segoe UI", 18, "bold")
            )
            loading_text.pack()
        
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor='center')
        self.loading_overlay.lift()

    def hide_loading(self):
        """Hide loading overlay."""
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.place_forget()

    def _fetch_worker(self, url: str):
        """Worker thread for fetching metadata."""
        try:
            metadata = self.youtube.get_video_info(url)
            self.after(0, lambda: self.handle_fetch_result(metadata))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.after(0, lambda: self.url_entry.configure(state='normal'))
            self.after(0, self.hide_loading)

    def handle_fetch_result(self, result):
        """Handle the result of metadata fetch."""
        if isinstance(result, PlaylistMetadata):
            self.current_playlist = result
            self.show_playlist(result)
        else:
            self.current_metadata = result
            self.show_single(result)
        
        self.show_view("results")

    def show_single(self, meta: VideoMetadata):
        """Show single video information."""
        # Clear previous results view
        if self.results_view:
            self.results_view.destroy()
        
        # Container
        self.results_view = tk.Frame(self.content_area, padx=16, pady=48)
        container = tk.Frame(self.results_view)
        container.pack(fill='both', expand=True)
        
        # Mini search bar
        search_frame = tk.Frame(container)
        search_frame.pack(fill='x', pady=(0, 32))
        
        # Input container with icon - flex-1
        input_container = tk.Frame(search_frame, relief="flat", bd=0)
        input_container.config(highlightthickness=1)
        input_container.pack(side='left', fill='x', expand=True, padx=(0, 12))
        
        # Link icon on left - absolute positioned in HTML
        icon_label = tk.Label(
            input_container, text="[LINK]", font=("Segoe UI", 10)
        )
        icon_label.pack(side='left', padx=16)
        
        search_entry = tk.Entry(
            input_container,
            relief="flat", bd=0,
            font=("Segoe UI", 11), highlightthickness=0
        )
        search_entry.pack(side='left', fill='x', expand=True, ipady=12)
        search_entry.insert(0, meta.original_url)
        search_entry.bind('<Return>', lambda e: self._search_from_entry(search_entry.get()))
        
        # Search button - h-12 px-6 rounded-xl
        search_btn = tk.Button(
            search_frame, text="Search", command=lambda: self._search_from_entry(search_entry.get())
        )
        search_btn.pack(side='left')
        
        # Results header
        header_frame = tk.Frame(container)
        header_frame.pack(fill='x', pady=(0, 24))
        
        # Title - text-2xl font-bold tracking-tight
        tk.Label(
            header_frame, text="Search Results", font=("Segoe UI", 24, "bold")
        ).pack(side='left')
        
        # Status indicator on right - flex items-center gap-4
        status_frame = tk.Frame(header_frame)
        status_frame.pack(side='right')
        
        status_label = tk.Label(
            status_frame, text="✓ Ready to download", font=("Segoe UI", 11)
        )
        status_label.pack(side='left')
        
        # Main card - bg-white dark:bg-[#192633]/80 border border-gray-200 dark:border-[#233648] rounded-2xl
        card = tk.Frame(container, relief="flat", bd=1)
        card.config(highlightthickness=1)
        card.pack(fill='x')
        
        # Grid layout: lg:grid-cols-12, lg:col-span-5 for thumbnail, lg:col-span-7 for options
        # Thumbnail column - lg:col-span-5 bg-black/5 dark:bg-black/20 p-6
        thumb_frame = tk.Frame(card, bg="#1a1a1a", width=400)  # black/20 equivalent
        thumb_frame.pack(side='left', fill='y', padx=24, pady=24)
        thumb_frame.pack_propagate(False)
        
        # Thumbnail container - rounded-xl overflow-hidden shadow-lg aspect-video
        thumb_container = tk.Frame(thumb_frame, bg="black", relief="flat", bd=0)
        thumb_container.pack(expand=True, fill='both')
        
        # Thumbnail label - make sure it's visible and properly sized
        self.result_thumb = tk.Label(
            thumb_container, bg="black", 
            anchor='center',
            text="Loading thumbnail...",
            fg="white",
            font=("Segoe UI", 10),
            compound='center'
        )
        self.result_thumb.pack(expand=True, fill='both')
        self.result_thumb.image = None  # Keep reference to prevent garbage collection
        
        # Info column - lg:col-span-7 p-6 md:p-8
        info_frame = tk.Frame(card, padx=32, pady=24)
        info_frame.pack(side='left', fill='both', expand=True)
        
        # Title - text-xl md:text-2xl font-bold mb-2
        title_label = tk.Label(
            info_frame, text=meta.title, font=("Segoe UI", 22, "bold"),
            wraplength=600, justify='left', anchor='w'
        )
        title_label.pack(anchor='w', pady=(0, 8))
        
        # Meta info - text-xs font-medium gap-4 mb-6
        meta_frame = tk.Frame(info_frame)
        meta_frame.pack(anchor='w', pady=(0, 24))
        
        tk.Label(
            meta_frame, text=f"Duration: {format_duration(meta.duration)}", font=("Segoe UI", 10)
        ).pack(side='left')
        
        tk.Label(
            meta_frame, text=" • ", font=("Segoe UI", 10)
        ).pack(side='left')
        
        tk.Label(
            meta_frame, text="YouTube", font=("Segoe UI", 10)
        ).pack(side='left')
        
        # Quality options (scrollable) - fixed height so download button is visible
        quality_frame = tk.Frame(info_frame, height=200)
        quality_frame.pack(fill='x', pady=(0, 8))
        quality_frame.pack_propagate(False)
        
        quality_canvas = tk.Canvas(quality_frame, highlightthickness=0, height=200)
        quality_scroll = ttk.Scrollbar(quality_frame, orient="vertical", command=quality_canvas.yview)
        quality_inner = tk.Frame(quality_canvas)
        
        quality_inner.bind("<Configure>", lambda e: quality_canvas.configure(scrollregion=quality_canvas.bbox("all")))
        quality_canvas.create_window((0, 0), window=quality_inner, anchor="nw")
        quality_canvas.configure(yscrollcommand=quality_scroll.set)
        
        quality_canvas.pack(side="left", fill="both", expand=True)
        quality_scroll.pack(side="right", fill="y")
        
        # Quality options
        self.quality_var = tk.StringVar()
        self.quality_map = {}
        opts = []
        
        for fmt in sorted(meta.formats, key=lambda f: (f.resolution if f.resolution != 'N/A' else '0x0'), reverse=True):
            # Only show video formats (video-only or combined video+audio)
            if fmt.vcodec == 'none':
                continue
            if fmt.resolution == 'N/A':
                continue
            # Skip formats without URLs
            if not fmt.url:
                continue
            
            label = f"{fmt.resolution} ({fmt.ext})"
            if label not in self.quality_map:
                self.quality_map[label] = fmt
                opts.append(label)
                
                # Radio button option
                opt_frame = tk.Frame(quality_inner, relief="flat", bd=1, padx=12, pady=12)
                opt_frame.config(highlightthickness=1)
                opt_frame.pack(fill='x', pady=2)
                
                rb = tk.Radiobutton(
                    opt_frame, text="", variable=self.quality_var, value=label
                )
                rb.pack(side='left', padx=(0, 12))
                
                # Quality info
                quality_info_frame = tk.Frame(opt_frame)
                quality_info_frame.pack(side='left', fill='x', expand=True)
                
                # Extract resolution text - convert "854x480" to "480p" or use note if available
                res_text = fmt.note if fmt.note and fmt.note != 'N/A' else fmt.resolution
                if 'x' in res_text:
                    parts = res_text.split('x')
                    if len(parts) == 2:
                        res_text = f"{parts[1]}p"
                elif res_text and not res_text.endswith('p'):
                    res_text = f"{res_text}p"
                
                # Quality row - font-bold text-sm with HD badge
                quality_row = tk.Frame(quality_info_frame)
                quality_row.pack(anchor='w')
                
                quality_label = tk.Label(
                    quality_row, text=res_text, font=("Segoe UI", 11, "bold")
                )
                quality_label.pack(side='left')
                
                # Add HD badge for high quality - bg-primary/10 text-primary text-[10px]
                if '1080' in res_text or '720' in res_text or '1080' in fmt.resolution or '720' in fmt.resolution:
                    hd_badge = tk.Label(
                        quality_row, text="HD",
                        fg="white", font=("Segoe UI", 8, "bold"),
                        padx=6, pady=2
                    )
                    hd_badge.pack(side='left', padx=(8, 0))
                
                # Format label - text-xs text-gray-500
                format_label = tk.Label(
                    quality_info_frame, text=fmt.ext.upper(), font=("Segoe UI", 9)
                )
                format_label.pack(anchor='w', pady=(2, 0))
                
                # Size label - text-sm font-medium on right
                filesize_mb = (fmt.filesize / (1024*1024)) if fmt.filesize and fmt.filesize > 0 else 0.0
                size_text = f"{filesize_mb:.1f} MB" if filesize_mb > 0 else "Unknown"
                size_label = tk.Label(
                    opt_frame, text=size_text,
                    font=("Segoe UI", 11)
                )
                size_label.pack(side='right')
        
        if opts:
            self.quality_var.set(opts[0])
        
        # Download button
        download_btn = tk.Button(
            info_frame, text="Download Video", command=self.add_single
        )
        download_btn.pack(fill='x', pady=8)
        
        # Load thumbnail
        threading.Thread(target=self._load_result_thumb, args=(meta.thumbnail_url,), daemon=True).start()
    
    def _search_from_entry(self, url: str):
        """Handle search from the results page search bar."""
        if url and url.strip():
            self.url_var.set(url.strip())
            self.fetch_info()

    def show_playlist(self, playlist: PlaylistMetadata):
        """Show playlist information."""
        # Similar to show_single but for playlists
        # For now, show a simplified version
        if self.results_view:
            self.results_view.destroy()
        
        self.results_view = tk.Frame(self.content_area, padx=24, pady=32)
        
        header = tk.Label(
            self.results_view, text=f"{playlist.title} ({len(playlist.entries)} videos)",
 font=("Segoe UI", 20, "bold")
        )
        header.pack(anchor='w', pady=(0, 16))
        
        # Playlist items
        list_frame = tk.Frame(self.results_view, padx=16, pady=16)
        list_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.pl_vars = []
        for i, entry in enumerate(playlist.entries):
            var = tk.BooleanVar(value=True)
            self.pl_vars.append((entry, var))
            
            row = tk.Frame(inner, pady=4)
            row.pack(fill='x')
            
            cb = tk.Checkbutton(
                row, variable=var,
                bd=0
            )
            cb.pack(side='left', padx=8)
            
            tk.Label(
                row, text=f"{i+1}. {entry.title}", font=("Segoe UI", 11)
            ).pack(side='left', padx=8)
            
            tk.Label(
                row, text=format_duration(entry.duration), font=("Segoe UI", 10)
            ).pack(side='right', padx=8)
        
        # Download button
        download_btn = tk.Button(
            self.results_view, text="Download Selected", command=self.process_playlist
        )
        download_btn.pack(pady=16)

    def _load_result_thumb(self, url: str):
        """Load result thumbnail."""
        try:
            import logging
            logging.info(f"Loading thumbnail from: {url}")
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            
            pil_img = Image.open(BytesIO(resp.content))
            # Resize to fit container (aspect-video ratio ~16:9, max 400x225)
            # Calculate proper aspect ratio
            max_width, max_height = 400, 225
            img_width, img_height = pil_img.size
            ratio = min(max_width / img_width, max_height / img_height)
            new_size = (int(img_width * ratio), int(img_height * ratio))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            
            tk_img = ImageTk.PhotoImage(pil_img)
            
            # Update UI in main thread - CRITICAL: keep reference as instance variable
            def update_thumb(img=tk_img):
                try:
                    if hasattr(self, 'result_thumb') and self.result_thumb.winfo_exists():
                        self.result_thumb.config(image=img, text="")
                        # Store reference as instance variable to prevent garbage collection
                        self.result_thumb.image = img
                        logging.info(f"Thumbnail loaded successfully: {img.width()}x{img.height()}")
                except Exception as e:
                    logging.error(f"Error updating thumbnail: {e}", exc_info=True)
            
            self.after(0, update_thumb)
        except Exception as e:
            import logging
            logging.error(f"Error loading thumbnail: {e}", exc_info=True)
            # Show placeholder on error
            self.after(0, lambda: self.result_thumb.config(
                text="📹\nNo thumbnail", 
                fg="white", 
                font=("Segoe UI", 16),
                compound='center'
            ))

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
            
            item = DownloadItem(
                self.downloads_container, self.current_metadata.title, fmt.url,
                best_audio.url if best_audio else None, save_path,
                thumb_url=self.current_metadata.thumbnail_url,
                headers=fmt.http_headers
            )
            item.start()
            self.download_items.append(item)
            
            # Switch to downloads view
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
        
        item = DownloadItem(
            self.downloads_container, meta.title, best.url,
            best_audio.url if best_audio else None, save_path,
            thumb_url=meta.thumbnail_url, headers=best.http_headers
        )
        item.start()
        self.download_items.append(item)
        self.update_downloads_display()

    def update_downloads_display(self):
        """Update downloads count display."""
        count = len([item for item in self.download_items if item.winfo_exists()])
        self.downloads_count_label.configure(text=f"({count})")
        self.downloads_canvas.update_idletasks()

    def pause_all_downloads(self):
        """Pause all active downloads."""
        for item in self.download_items:
            if item.winfo_exists() and hasattr(item, 'toggle_pause'):
                if not item.is_paused:
                    item.toggle_pause()

    def resume_all_downloads(self):
        """Resume all paused downloads."""
        for item in self.download_items:
            if item.winfo_exists() and hasattr(item, 'toggle_pause'):
                if item.is_paused:
                    item.toggle_pause()

    def open_settings(self):
        """Open settings modal."""
        self.settings_modal.deiconify()
        self.settings_modal.lift()
        self.settings_modal.grab_set()  # Set grab when showing
        self.settings_modal.focus()

    def close_settings(self):
        """Close settings modal."""
        self.settings_modal.grab_release()  # Release grab before hiding
        self.settings_modal.withdraw()

    def browse_download_path(self):
        """Browse for download path."""
        d = filedialog.askdirectory()
        if d:
            self.path_var.set(d)

    def save_settings(self):
        """Save settings."""
        path = self.path_var.get()
        if path:
            self.config.set_download_path(path)
        self.close_settings()
