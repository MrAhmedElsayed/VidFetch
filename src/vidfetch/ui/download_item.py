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


class DownloadTask:
    """Handles the download logic and state (Model)."""
    def __init__(self, title: str, video_url: Optional[str], audio_url: Optional[str], 
                 output_path: Path, thumb_url: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        # Props
        self.title_text = title
        self.output_path = output_path
        self.video_url = video_url
        self.audio_url = audio_url
        self.thumb_url = thumb_url
        self.headers = headers or {}
        
        # Derivatives
        output_ext = output_path.suffix.lower()
        if output_ext == '.webm':
            video_ext = '.webm'
            audio_ext = '.webm'
        else:
            video_ext = '.mp4'
            audio_ext = '.m4a'
            
        temp_base = output_path.stem
        self.v_path = output_path.parent / f"temp_video_{temp_base}{video_ext}"
        self.a_path = output_path.parent / f"temp_audio_{temp_base}{audio_ext}"
        
        # State
        self.is_paused = False
        self.is_downloading = False
        self.is_cancelled = False
        self.error_msg = None
        self.progress = 0.0
        self.status_text = "Waiting..."
        self.speed_text = ""
        self.time_text = ""
        
        # Internal
        self.dl_instance = None
        self.start_time = None
        self.downloaded_bytes = 0
        self.total_bytes = 0
        
        # Callbacks for UI updates: func(task)
        self.observers = []

    def start(self):
        """Start the download."""
        if self.is_downloading:
            return
        self.is_downloading = True
        self.is_paused = False
        self.is_cancelled = False
        self.error_msg = None
        self.start_time = time.time()
        self._notify()
        
        threading.Thread(target=self._run_download, daemon=True).start()

    def toggle_pause(self):
        """Toggle pause/resume."""
        if self.is_paused:
            self.start() 
        else:
            self.is_paused = True
            self.is_downloading = False
            self.status_text = "Paused"
            if self.dl_instance:
                self.dl_instance.stop()
            self._notify()
                
    def cancel(self):
        """Cancel the download."""
        self.is_paused = True
        self.is_downloading = False
        self.is_cancelled = True
        if self.dl_instance:
            self.dl_instance.stop()
        self._notify()

    def add_observer(self, callback):
        self.observers.append(callback)
        # Notify immediately with current state
        try:
            callback(self)
        except Exception:
            pass
            
    def remove_observer(self, callback):
        if callback in self.observers:
            self.observers.remove(callback)

    def _notify(self):
        for cb in self.observers:
            try:
                cb(self)
            except Exception:
                pass

    def _run_download(self):
        """Run the download process."""
        try:
            video_complete = False
            audio_complete = False
            
            if self.video_url:
                try:
                    self.dl_instance = SmartDownloader(
                        self.video_url, self.v_path, 
                        progress_callback=lambda p, c, t: self._update_progress(p, "Video", c, t),
                        headers=self.headers
                    )
                    self.dl_instance.start()
                    video_complete = self.v_path.exists() and self.v_path.stat().st_size > 0
                except Exception as e:
                    import logging
                    logging.error(f"Video download failed: {e}", exc_info=True)
                    raise RuntimeError(f"Video download failed: {str(e)}")
                
                if self.is_paused or self.is_cancelled:
                    return 
            
            if self.audio_url:
                try:
                    self.dl_instance = SmartDownloader(
                        self.audio_url, self.a_path,
                        progress_callback=lambda p, c, t: self._update_progress(p, "Audio", c, t),
                        headers=self.headers
                    )
                    self.dl_instance.start()
                    audio_complete = self.a_path.exists() and self.a_path.stat().st_size > 0
                except Exception as e:
                    import logging
                    logging.error(f"Audio download failed: {e}", exc_info=True)
                    raise RuntimeError(f"Audio download failed: {str(e)}")
                
            if self.is_paused or self.is_cancelled:
                return
            
            if self.video_url and self.audio_url:
                if not video_complete:
                    raise RuntimeError("Video file download failed or is incomplete")
                if not audio_complete:
                    raise RuntimeError("Audio file download failed or is incomplete")
                
                self.status_text = "Processing..."
                self.progress = 50.0
                self._notify()
                
                MediaMuxer.merge(self.v_path, self.a_path, self.output_path)
                
                self.progress = 100.0
                
                if self.v_path.exists():
                    self.v_path.unlink()
                if self.a_path.exists():
                    self.a_path.unlink()
            elif self.video_url:
                if video_complete and self.v_path.exists():
                    file_size = self.v_path.stat().st_size
                    if file_size < 1024 * 100:
                        raise RuntimeError(f"Downloaded file is too small ({file_size} bytes)")
                    self.v_path.replace(self.output_path)
                else:
                    raise RuntimeError("Video file download failed")
            elif self.audio_url:
                if audio_complete and self.a_path.exists():
                    self.a_path.replace(self.output_path)
                else:
                    raise RuntimeError("Audio file download failed")

            self.status_text = "Completed"
            self.progress = 100.0
            self.is_downloading = False
            self._notify()
            
        except Exception as e:
            if not self.is_paused and not self.is_cancelled:
                import logging
                logging.error(f"Task error: {e}", exc_info=True)
                self.error_msg = str(e)[:50]
                self.status_text = f"Error: {self.error_msg}"
                self.is_downloading = False
                self._notify()

    def _update_progress(self, percent: float, text_prefix: str, current_bytes: int = 0, total_bytes: int = 0):
        if self.is_paused or self.is_cancelled:
            return
        
        self.progress = percent
        self.status_text = f"{percent:.0f}%"
        self.downloaded_bytes = current_bytes
        self.total_bytes = total_bytes
        
        elapsed = time.time() - (self.start_time or time.time())
        if elapsed > 0 and current_bytes > 0:
            speed_mbps = (current_bytes / (1024 * 1024)) / elapsed
            self.speed_text = f"{speed_mbps:.1f} MB/s"
            
            if total_bytes > 0 and speed_mbps > 0:
                remaining_bytes = total_bytes - current_bytes
                remaining_mb = remaining_bytes / (1024 * 1024)
                eta_seconds = remaining_mb / speed_mbps if speed_mbps > 0 else 0
                
                if eta_seconds < 60:
                    self.time_text = f"{int(eta_seconds)}s remaining"
                elif eta_seconds < 3600:
                    self.time_text = f"{int(eta_seconds / 60)}m remaining"
                else:
                    self.time_text = f"{int(eta_seconds / 3600)}h remaining"
            else:
                self.time_text = ""
        
        self._notify()


class DownloadItem(ctk.CTkFrame):
    """View widget for a DownloadTask."""
    
    def __init__(self, parent, task: DownloadTask):
        super().__init__(parent)
        self.task = task
        self.setup_ui()
        
        # Subscribe to task updates
        self.task.add_observer(self.on_task_update)
        
        # Load thumbnail if needed
        if self.task.thumb_url and not hasattr(self.task, '_cached_thumb'):
            threading.Thread(target=self._load_thumb, daemon=True).start()
            
    def destroy(self):
        # Unsubscribe before destroying
        self.task.remove_observer(self.on_task_update)
        super().destroy()
        
    def setup_ui(self):
        """Setup card-style UI."""
        self.configure(
            fg_color=("#1e293b", "#1e293b"),
            corner_radius=12,
            border_width=1,
            border_color=("#334155", "#334155")
        )
        
        # Inner wrapper
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=4, pady=4)
        
        # 1. Thumbnail
        thumb_box = ctk.CTkFrame(inner, fg_color="transparent", width=144, height=81)
        thumb_box.pack(side="left", padx=(12, 16), pady=12)
        thumb_box.pack_propagate(False)
        
        self.lbl_thumb = ctk.CTkLabel(
            thumb_box, text="📹", fg_color="#374151", corner_radius=8,
            width=144, height=81, font=("Helvetica", 24)
        )
        self.lbl_thumb.pack(fill="both", expand=True)
        # Use cached thumb if available
        if hasattr(self.task, '_cached_thumb'):
             self.lbl_thumb.configure(image=self.task._cached_thumb, text="")
        
        # Format Badge
        format_text = "MP4"
        if self.task.output_path.suffix.lower() in ['.mp3', '.m4a']:
            format_text = "MP3"
        elif self.task.output_path.suffix.lower() == '.webm':
            format_text = "WEBM"
            
        self.format_badge = ctk.CTkLabel(
            self.lbl_thumb, text=format_text, 
            font=("Helvetica", 10, "bold"),
            fg_color="#000000", text_color="white", corner_radius=4
        )
        self.format_badge.place(relx=0.96, rely=0.94, anchor="se")
        
        # 2. Actions
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(side="right", padx=(0, 16), fill="y")
        
        ctk.CTkFrame(actions, width=1, fg_color="#334155", height=40).pack(side="left", fill="y", padx=(0, 16), pady=20)
        
        self.btn_pause = ctk.CTkButton(
            actions, text="⏸", command=self.task.toggle_pause, width=40, height=40,
            fg_color="transparent", hover_color="#3b82f6", corner_radius=20,
            font=("Helvetica", 16)
        )
        self.btn_pause.pack(side="left", padx=4)
        
        btn_cancel = ctk.CTkButton(
            actions, text="✕", command=self.cancel_task, width=40, height=40,
            fg_color="transparent", hover_color="#7f1d1d", corner_radius=20,
            font=("Helvetica", 16)
        )
        btn_cancel.pack(side="left", padx=4)
        
        # 3. Info
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=12)
        
        # Row 1
        row1 = ctk.CTkFrame(info, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 4))
        
        self.lbl_title = ctk.CTkLabel(
            row1, text=self.task.title_text,
            font=("Helvetica", 14, "bold"), text_color="white",
            anchor='w', wraplength=350
        )
        self.lbl_title.pack(side="left", padx=(0, 12))
        
        ctk.CTkLabel(
            row1, text="1080p",
            font=("Helvetica", 10, "bold"),
            fg_color="#0f172a", text_color="#94a3b8",
            corner_radius=6, padx=8, pady=2
        ).pack(side="left", padx=4)
        
        # Row 2
        row2 = ctk.CTkFrame(info, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 0))
        
        meta = ctk.CTkFrame(row2, fg_color="transparent")
        meta.pack(fill="x", pady=(0, 4))
        
        self.lbl_status = ctk.CTkLabel(
            meta, text="0%",
            font=("Helvetica", 12, "bold"), text_color="#3b82f6"
        )
        self.lbl_status.pack(side="left")
        
        stats = ctk.CTkFrame(meta, fg_color="transparent")
        stats.pack(side="right")
        
        self.lbl_speed = ctk.CTkLabel(
            stats, text="",
            font=("Helvetica", 11), text_color="#94a3b8"
        )
        self.lbl_speed.pack(side="left", padx=(0, 16))
        
        self.lbl_time = ctk.CTkLabel(
            stats, text="",
            font=("Helvetica", 11), text_color="#94a3b8"
        )
        self.lbl_time.pack(side="left")
        
        self.progress = ctk.CTkProgressBar(
            row2, height=6, corner_radius=3,
            progress_color="#3b82f6", fg_color="#334155"
        )
        self.progress.set(0)
        self.progress.pack(fill='x')

    def cancel_task(self):
        self.task.cancel()
        # The parent view should handle removing the widget if needed, 
        # or we update UI to show cancelled state. 
        # For now, let's keep it in list but maybe dim it? 
        # Or remove it? The old logic destroyed it.
        # Let's ask parent to reload view or handle removal.
        # Since we're in a list in MainWindow, we should let MainWindow handle removal.
        # But for now, just update state.
        pass

    def on_task_update(self, task):
        """Update UI based on task state."""
        # Use after() to ensure thread safety with Tkinter
        self.after(0, self._update_ui_safe)

    def _update_ui_safe(self):
        if not self.winfo_exists():
            return
            
        # Update progress and text
        self.progress.set(self.task.progress / 100.0)
        
        if self.task.error_msg:
            self.lbl_status.configure(text=self.task.status_text, text_color="red")
            self.lbl_speed.configure(text="Failed", text_color="red")
        elif self.task.is_cancelled:
            self.lbl_status.configure(text="Cancelled", text_color="#94a3b8")
            self.lbl_speed.configure(text="-", text_color="#94a3b8")
        else:
            self.lbl_status.configure(text=self.task.status_text, text_color="#3b82f6")
            self.lbl_speed.configure(text=self.task.speed_text, text_color="#94a3b8")
            self.lbl_time.configure(text=self.task.time_text)
            
        # Update pause button
        if self.task.is_paused:
            self.btn_pause.configure(text="▶")
        elif self.task.is_cancelled or self.task.progress >= 100:
             self.btn_pause.configure(state='disabled')
        else:
            self.btn_pause.configure(text="⏸", state='normal')

    def _load_thumb(self):
        try:
            resp = requests.get(self.task.thumb_url, timeout=10)
            pil_img = Image.open(BytesIO(resp.content))
            pil_img = pil_img.resize((144, 81), Image.Resampling.LANCZOS)
            ctk_img = CTkImage(light_image=pil_img, dark_image=pil_img, size=(144, 81))
            self.task._cached_thumb = ctk_img
            self.after(0, lambda: self.lbl_thumb.configure(image=ctk_img, text=""))
            self.lbl_thumb.image = ctk_img
        except Exception:
            pass

