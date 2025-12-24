"""Download queue item component."""

import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Dict
from io import BytesIO
import requests
from PIL import Image, ImageTk

from ..core import SmartDownloader, MediaMuxer
# Using standard Tkinter widgets only


class DownloadItem(tk.Frame):
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
        self.configure(relief="flat", bd=1)
        self.pack(fill='x', pady=0, padx=0)
        
        # Configure grid
        self.columnconfigure(1, weight=1)  # Title column expands
        self.columnconfigure(2, weight=2)  # Progress column expands
        
        # 1. Preview (Thumbnail) - Column 0 - h-12 w-12 rounded-lg matching HTML
        thumb_container = tk.Frame(self, padx=24, pady=16)
        thumb_container.grid(row=0, column=0, sticky='n')
        
        # Thumbnail - h-12 w-12 rounded-lg shadow-sm
        self.lbl_thumb = tk.Label(
            thumb_container, bg="black", width=12, height=12,
            relief="flat", bd=0
        )
        self.lbl_thumb.pack()
        
        # 2. Title & Format - Column 1
        title_frame = tk.Frame(self, padx=24, pady=16)
        title_frame.grid(row=0, column=1, sticky='nw')
        
        self.lbl_title = tk.Label(
            title_frame, text=self.title_text,
            font=("Segoe UI", 11), anchor='w',
            wraplength=300
        )
        self.lbl_title.pack(anchor='w')
        
        # Format badges
        format_frame = tk.Frame(title_frame)
        format_frame.pack(anchor='w', pady=(4, 0))
        
        # Determine format from URL/ext
        format_text = "MP4"
        if self.output_path.suffix.lower() == '.mp3' or self.output_path.suffix.lower() == '.m4a':
            format_text = "MP3"
        
        # Format badges - matching HTML: text-[10px] font-medium bg-slate-100 dark:bg-slate-700
        self.format_badge = tk.Label(
            format_frame, text=format_text,
            font=("Segoe UI", 8),
            padx=6, pady=2, relief="flat"
        )
        self.format_badge.pack(side='left', padx=(0, 4))
        
        # Quality badge (will be updated)
        self.quality_badge = tk.Label(
            format_frame, text="1080p",
            font=("Segoe UI", 8),
            padx=6, pady=2, relief="flat"
        )
        self.quality_badge.pack(side='left')
        
        # 3. Progress - Column 2
        progress_frame = tk.Frame(self, padx=24, pady=16)
        progress_frame.grid(row=0, column=2, sticky='ew')
        progress_frame.columnconfigure(0, weight=1)
        
        # Percentage label
        self.progress_percent = tk.Label(
            progress_frame, text="0%",
            font=("Segoe UI", 11, "bold")
        )
        self.progress_percent.pack(anchor='w', pady=(0, 4))
        
        # Progress bar - h-2 rounded-full matching HTML
        self.progress = ttk.Progressbar(
            progress_frame, orient='horizontal', mode='determinate',
            length=200
        )
        self.progress.pack(fill='x')
        
        # Style progress bar to match HTML (h-2 rounded-full)
        style = ttk.Style()
        style.configure("Horizontal.TProgressbar", thickness=8)
        
        # 4. Stats - Column 3
        stats_frame = tk.Frame(self, padx=24, pady=16)
        stats_frame.grid(row=0, column=3, sticky='n')
        
        self.speed_label = tk.Label(
            stats_frame, text="0 MB/s",
            font=("Segoe UI", 11)
        )
        self.speed_label.pack(anchor='w')
        
        self.time_label = tk.Label(
            stats_frame, text="Calculating...",
            font=("Segoe UI", 9)
        )
        self.time_label.pack(anchor='w', pady=(2, 0))
        
        # 5. Actions - Column 4
        actions_frame = tk.Frame(self, padx=24, pady=16)
        actions_frame.grid(row=0, column=4, sticky='ne')
        
        # Action buttons - matching HTML: p-2 rounded-lg text-slate-400 hover:text-primary hover:bg-primary/10
        self.btn_pause = tk.Button(
            actions_frame, text="⏸", command=self.toggle_pause
        )
        self.btn_pause.pack(side='left', padx=2)
        
        btn_cancel = tk.Button(
            actions_frame, text="✕", command=self.cancel
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
            tk_img = ImageTk.PhotoImage(pil_img)
            self.after(0, lambda: self.lbl_thumb.config(image=tk_img, width=0, height=0))
            self.lbl_thumb.image = tk_img
        except Exception:
            pass

    def start(self):
        """Start the download."""
        if self.is_downloading:
            return
        self.is_downloading = True
        self.is_paused = False
        self.btn_pause.config(text="⏸")
        
        threading.Thread(target=self._run_download, daemon=True).start()

    def toggle_pause(self):
        """Toggle pause/resume."""
        if self.is_paused:
            self.start() 
        else:
            self.is_paused = True
            self.is_downloading = False
            self.btn_pause.config(text="▶")
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
                
                self.after(0, lambda: self.progress.configure(mode='indeterminate'))
                self.after(0, lambda: self.progress_percent.config(text="Processing..."))
                self.after(0, self.progress.start)
                
                MediaMuxer.merge(self.v_path, self.a_path, self.output_path)
                
                self.after(0, self.progress.stop)
                self.after(0, lambda: self.progress.configure(mode='determinate', value=100))
                
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

            self.after(0, lambda: self.progress_percent.config(text="Completed"))
            self.after(0, lambda: self.progress.configure(value=100))
            self.btn_pause.config(state='disabled')
            
        except Exception as e:
            if not self.is_paused:
                import logging
                logging.error(f"Download error for {self.title_text}: {e}", exc_info=True)
                error_msg = str(e)[:50]  # Truncate long errors
                self.after(0, lambda msg=error_msg: self.progress_percent.config(
                    text=f"Error: {msg}", foreground="red"
                ))
                self.after(0, lambda: self.speed_label.config(text="Failed", foreground="red"))
                self.after(0, lambda: self.time_label.config(text=""))

    def _update_ui(self, percent: float, text_prefix: str, current_bytes: int = 0, total_bytes: int = 0):
        """Update UI with progress."""
        if self.is_paused:
            return
        
        self.downloaded_bytes = current_bytes
        self.total_bytes = total_bytes
        
        # Update progress bar and percentage
        self.after(0, lambda: self.progress.configure(value=percent))
        self.after(0, lambda: self.progress_percent.config(text=f"{percent:.0f}%"))
        
        # Calculate speed and ETA
        elapsed = time.time() - (self.start_time or time.time())
        if elapsed > 0 and current_bytes > 0:
            speed_mbps = (current_bytes / (1024 * 1024)) / elapsed
            self.after(0, lambda s=speed_mbps: self.speed_label.config(text=f"{s:.1f} MB/s"))
            
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
                
                self.after(0, lambda t=eta_text: self.time_label.config(text=t))

