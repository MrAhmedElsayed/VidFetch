"""Download queue item component."""

import threading
import time
import customtkinter as ctk
import tkinter as tk  # Still needed for some widgets
from tkinter import ttk
from pathlib import Path
from typing import Optional, Dict
from io import BytesIO
import requests
from PIL import Image, ImageTk
from customtkinter import CTkImage

from ..core import SmartDownloader, MediaMuxer
from .components import COLORS


class DownloadItem(ctk.CTkFrame):
    """Represents a single item in the download queue with Pause/Resume and Thumbnail."""
    
    def __init__(self, parent, title: str, video_url: Optional[str], audio_url: Optional[str], 
                 output_path: Path, thumb_url: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        
        # Props
        self.title_text = title
        self.output_path = output_path
        self.video_url = video_url
        self.audio_url = audio_url
        self.thumb_url = thumb_url
        self.headers = headers or {}
        
        # Use proper extensions for temp files based on output format
        # Match the output extension for video, use appropriate audio extension
        output_ext = output_path.suffix.lower()
        if output_ext == '.webm':
            video_ext = '.webm'
            audio_ext = '.webm'
        else:
            video_ext = '.mp4'  # Default to mp4
            audio_ext = '.m4a'  # Use m4a for mp4 audio
        
        # Create temp file names with proper extensions
        temp_base = output_path.stem
        self.v_path = output_path.parent / f"temp_video_{temp_base}{video_ext}"
        self.a_path = output_path.parent / f"temp_audio_{temp_base}{audio_ext}"
        
        # State
        self.is_paused = False
        self.is_downloading = False
        self.dl_instance = None 
        
        self.setup_ui()
        if self.thumb_url:
            threading.Thread(target=self._load_thumb, daemon=True).start()
        
    def setup_ui(self):
        """Setup table-style UI matching web design."""
        # Table row layout: [Preview] [Title & Format] [Progress] [Stats] [Actions]
        self.pack(fill='x', pady=0, padx=0)
        
        # Configure grid
        self.columnconfigure(1, weight=1)  # Title column expands
        self.columnconfigure(2, weight=2)  # Progress column expands
        
        # 1. Preview (Thumbnail) - Column 0 - h-12 w-12 rounded-lg matching HTML
        thumb_container = ctk.CTkFrame(self, fg_color="transparent")
        thumb_container.grid(row=0, column=0, sticky='n', padx=24, pady=16)
        
        # Thumbnail - h-12 w-12 rounded-lg shadow-sm
        self.lbl_thumb = ctk.CTkLabel(
            thumb_container, text="", fg_color="black", width=48, height=48
        )
        self.lbl_thumb.pack()
        
        # 2. Title & Format - Column 1
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky='nw', padx=24, pady=16)
        
        self.lbl_title = ctk.CTkLabel(
            title_frame, text=self.title_text,
            font=("Segoe UI", 11), anchor='w',
            wraplength=300
        )
        self.lbl_title.pack(anchor='w')
        
        # Format badges
        format_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        format_frame.pack(anchor='w', pady=(4, 0))
        
        # Determine format from URL/ext
        format_text = "MP4"
        if self.output_path.suffix.lower() == '.mp3' or self.output_path.suffix.lower() == '.m4a':
            format_text = "MP3"
        
        # Format badges - matching HTML: text-[10px] font-medium bg-slate-100 dark:bg-slate-700
        self.format_badge = ctk.CTkLabel(
            format_frame, text=format_text,
            font=("Segoe UI", 8),
            padx=6, pady=2
        )
        self.format_badge.pack(side='left', padx=(0, 4))
        
        # Quality badge (will be updated)
        self.quality_badge = ctk.CTkLabel(
            format_frame, text="1080p",
            font=("Segoe UI", 8),
            padx=6, pady=2
        )
        self.quality_badge.pack(side='left')
        
        # 3. Progress - Column 2
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=0, column=2, sticky='ew', padx=24, pady=16)
        progress_frame.columnconfigure(0, weight=1)
        
        # Percentage label
        self.progress_percent = ctk.CTkLabel(
            progress_frame, text="0%",
            font=("Segoe UI", 11, "bold")
        )
        self.progress_percent.pack(anchor='w', pady=(0, 4))
        
        # Progress bar - h-2 rounded-full matching HTML
        self.progress = ctk.CTkProgressBar(progress_frame)
        self.progress.set(0)
        self.progress.pack(fill='x')
        
        # 4. Stats - Column 3
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=0, column=3, sticky='n', padx=24, pady=16)
        
        self.speed_label = ctk.CTkLabel(
            stats_frame, text="0 MB/s",
            font=("Segoe UI", 11)
        )
        self.speed_label.pack(anchor='w')
        
        self.time_label = ctk.CTkLabel(
            stats_frame, text="Calculating...",
            font=("Segoe UI", 9)
        )
        self.time_label.pack(anchor='w', pady=(2, 0))
        
        # 5. Actions - Column 4
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=0, column=4, sticky='ne', padx=24, pady=16)
        
        # Action buttons - matching HTML: p-2 rounded-lg text-slate-400 hover:text-primary hover:bg-primary/10
        self.btn_pause = ctk.CTkButton(
            actions_frame, text="⏸", command=self.toggle_pause, width=30, height=30
        )
        self.btn_pause.pack(side='left', padx=2)
        
        btn_cancel = ctk.CTkButton(
            actions_frame, text="✕", command=self.cancel, width=30, height=30
        )
        btn_cancel.pack(side='left', padx=2)
        
        # Track download stats
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.start_time = time.time()

    def _load_thumb(self):
        """Load thumbnail image asynchronously."""
        try:
            resp = requests.get(self.thumb_url, timeout=10)
            pil_img = Image.open(BytesIO(resp.content))
            pil_img.thumbnail((48, 48))  # Smaller for table
            ctk_img = CTkImage(light_image=pil_img, dark_image=pil_img, size=(48, 48))
            self.after(0, lambda: self.lbl_thumb.configure(image=ctk_img, text=""))
            self.lbl_thumb.image = ctk_img
        except Exception:
            pass

    def start(self):
        """Start the download."""
        if self.is_downloading:
            return
        self.is_downloading = True
        self.is_paused = False
        self.btn_pause.configure(text="⏸")
        
        threading.Thread(target=self._run_download, daemon=True).start()

    def toggle_pause(self):
        """Toggle pause/resume."""
        if self.is_paused:
            self.start() 
        else:
            self.is_paused = True
            self.is_downloading = False
            self.btn_pause.configure(text="▶")
            if self.dl_instance:
                self.dl_instance.stop()
                
    def cancel(self):
        """Cancel the download."""
        self.is_paused = True
        self.is_downloading = False
        if self.dl_instance:
            self.dl_instance.stop()
        self.destroy()

    def _run_download(self):
        """Run the download process."""
        try:
            video_complete = False
            audio_complete = False
            
            if self.video_url:
                try:
                    # Status updated via progress callback
                    self.dl_instance = SmartDownloader(
                        self.video_url, self.v_path, 
                        progress_callback=lambda p, c, t: self._update_ui(p, "Video", c, t),
                        headers=self.headers
                    )
                    self.dl_instance.start()  # This is blocking, waits for completion
                    video_complete = self.v_path.exists() and self.v_path.stat().st_size > 0
                except Exception as e:
                    import logging
                    logging.error(f"Video download failed: {e}", exc_info=True)
                    raise RuntimeError(f"Video download failed: {str(e)}")
                
                if self.is_paused:
                    return 
            
            if self.audio_url:
                try:
                    # Status updated via progress callback
                    self.dl_instance = SmartDownloader(
                        self.audio_url, self.a_path,
                        progress_callback=lambda p, c, t: self._update_ui(p, "Audio", c, t),
                        headers=self.headers
                    )
                    self.dl_instance.start()  # This is blocking, waits for completion
                    audio_complete = self.a_path.exists() and self.a_path.stat().st_size > 0
                except Exception as e:
                    import logging
                    logging.error(f"Audio download failed: {e}", exc_info=True)
                    raise RuntimeError(f"Audio download failed: {str(e)}")
                
            if self.is_paused:
                return
            
            if self.video_url and self.audio_url:
                # Verify files are complete before muxing
                if not video_complete:
                    raise RuntimeError("Video file download failed or is incomplete")
                if not audio_complete:
                    raise RuntimeError("Audio file download failed or is incomplete")
                
                self.after(0, lambda: self.progress_percent.configure(text="Processing..."))
                self.after(0, lambda: self.progress.set(0.5))  # Show 50% during muxing
                
                MediaMuxer.merge(self.v_path, self.a_path, self.output_path)
                
                self.after(0, lambda: self.progress.set(1.0))
                
                if self.v_path.exists():
                    self.v_path.unlink()
                if self.a_path.exists():
                    self.a_path.unlink()
            elif self.video_url:
                if video_complete and self.v_path.exists():
                    # Verify file size is reasonable (not just a few KB)
                    file_size = self.v_path.stat().st_size
                    if file_size < 1024 * 100:  # Less than 100KB is suspicious
                        raise RuntimeError(f"Downloaded file is too small ({file_size} bytes), download may have failed")
                    self.v_path.replace(self.output_path)
                else:
                    raise RuntimeError("Video file download failed or is incomplete")
            elif self.audio_url:
                if audio_complete and self.a_path.exists():
                    self.a_path.replace(self.output_path)
                else:
                    raise RuntimeError("Audio file download failed or is incomplete")

            self.after(0, lambda: self.progress_percent.configure(text="Completed"))
            self.after(0, lambda: self.progress.set(1.0))
            self.btn_pause.configure(state='disabled')
            
        except Exception as e:
            if not self.is_paused:
                import logging
                logging.error(f"Download error for {self.title_text}: {e}", exc_info=True)
                error_msg = str(e)[:50]  # Truncate long errors
                self.after(0, lambda msg=error_msg: self.progress_percent.configure(
                    text=f"Error: {msg}", text_color="red"
                ))
                self.after(0, lambda: self.speed_label.configure(text="Failed", text_color="red"))
                self.after(0, lambda: self.time_label.configure(text=""))

    def _update_ui(self, percent: float, text_prefix: str, current_bytes: int = 0, total_bytes: int = 0):
        """Update UI with progress."""
        if self.is_paused:
            return
        
        self.downloaded_bytes = current_bytes
        self.total_bytes = total_bytes
        
        # Update progress bar and percentage
        self.after(0, lambda p=percent: self.progress.set(p / 100.0))
        self.after(0, lambda p=percent: self.progress_percent.configure(text=f"{p:.0f}%"))
        
        # Calculate speed and ETA
        elapsed = time.time() - (self.start_time or time.time())
        if elapsed > 0 and current_bytes > 0:
            speed_mbps = (current_bytes / (1024 * 1024)) / elapsed
            self.after(0, lambda s=speed_mbps: self.speed_label.configure(text=f"{s:.1f} MB/s"))
            
            if total_bytes > 0 and speed_mbps > 0:
                remaining_bytes = total_bytes - current_bytes
                remaining_mb = remaining_bytes / (1024 * 1024)
                eta_seconds = remaining_mb / speed_mbps if speed_mbps > 0 else 0
                
                if eta_seconds < 60:
                    eta_text = f"{int(eta_seconds)}s remaining"
                elif eta_seconds < 3600:
                    eta_text = f"{int(eta_seconds / 60)}m remaining"
                else:
                    eta_text = f"{int(eta_seconds / 3600)}h remaining"
                
                self.after(0, lambda t=eta_text: self.time_label.configure(text=t))

