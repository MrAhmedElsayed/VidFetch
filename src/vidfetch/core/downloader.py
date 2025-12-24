"""Robust chunked file downloading with multi-threading."""

import threading
from pathlib import Path
from typing import Optional, Callable, Dict
import concurrent.futures
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SmartDownloader:
    """Handles robust chunked file downloading with multi-threading."""
    
    def __init__(self, url: str, output_path: Path, max_threads: int = 8, 
                 progress_callback: Optional[Callable[[float, int, int], None]] = None,
                 headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.output_path = Path(output_path)
        self.max_threads = max_threads
        self.progress_callback = progress_callback
        self.headers = headers or {}

        self._stop_event = threading.Event()
        self._downloaded_bytes = 0
        self._total_bytes = 0
        self._lock = threading.Lock()
        
        # Setup Robust Session
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        if self.headers:
            self.session.headers.update(self.headers)

    def start(self):
        """Starts the download process."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Get total size
        try:
            head_resp = self.session.head(self.url, allow_redirects=True, timeout=10)
            self._total_bytes = int(head_resp.headers.get('content-length', 0))
        except Exception:
            pass

        # Fallback if HEAD failed
        if self._total_bytes == 0:
            try:
                with self.session.get(self.url, stream=True, timeout=10) as r:
                    self._total_bytes = int(r.headers.get('content-length', 0))
            except Exception:
                self._total_bytes = 0

        # If we still don't know the size, or it's too small to split, use single thread
        # Also use single thread for YouTube URLs as they may not support range requests reliably
        if self._total_bytes < 1024 * 1024 or 'googlevideo.com' in self.url or 'youtube.com' in self.url:
            self._download_single_thread()
            return

        # 2. Plan Segments & Download to Temp Files
        chunk_size = self._total_bytes // self.max_threads
        futures = []
        temp_files = []  # Tuples of (start_byte, path)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            for i in range(self.max_threads):
                start = i * chunk_size
                end = start + chunk_size - 1
                if i == self.max_threads - 1:
                    end = self._total_bytes - 1
                
                part_path = self.output_path.with_name(f"{self.output_path.name}.part{i}")
                temp_files.append((start, part_path))
                
                futures.append(executor.submit(self._download_chunk, start, end, part_path))
            
            # Wait for all
            for future in concurrent.futures.as_completed(futures):
                if self._stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    future.result()
                except Exception as e:
                    self._stop_event.set()
                    raise e
        
        if self._stop_event.is_set():
            return

        # 3. Merge Parts
        try:
            with open(self.output_path, 'wb') as outfile:
                for _, part_path in temp_files:
                    with open(part_path, 'rb') as infile:
                        # Read in chunks to avoid memory spike
                        while True:
                            chunk = infile.read(1024*1024)
                            if not chunk:
                                break
                            outfile.write(chunk)
                    # clean up part immediately
                    part_path.unlink()
            
            # Integrity Check
            if self._total_bytes > 0:
                actual_size = self.output_path.stat().st_size
                if actual_size < self._total_bytes:
                    raise ValueError(f"Download incomplete: Expected {self._total_bytes}, got {actual_size}")

        except Exception as e:
            raise e

        # Final check
        if self.progress_callback:
            self.progress_callback(100.0, self._total_bytes, self._total_bytes)

    def _download_chunk(self, start, end, part_path):
        if self._stop_event.is_set():
            return
        
        headers = {'Range': f'bytes={start}-{end}'}
        expected_size = end - start + 1
        downloaded = 0
        
        try:
            with self.session.get(self.url, headers=headers, stream=True, timeout=60) as r:
                # Check if server supports range requests
                if r.status_code == 206:  # Partial Content
                    r.raise_for_status()
                elif r.status_code == 200:  # Full content (range not supported)
                    # Server doesn't support range, download from start
                    # This shouldn't happen in multi-threaded mode, but handle it
                    pass
                else:
                    r.raise_for_status()
                
                with open(part_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*64):
                        if self._stop_event.is_set():
                            break
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            with self._lock:
                                self._downloaded_bytes += len(chunk)
                                self._report_progress(self._downloaded_bytes)
                
                # Verify chunk is complete
                if expected_size > 0 and downloaded < expected_size:
                    raise ValueError(f"Chunk incomplete: expected {expected_size}, got {downloaded}")

        except Exception as e:
            raise e

    def _download_single_thread(self):
        """Fallback for unknown size."""
        mode = 'wb'
        try:
            with self.session.get(self.url, stream=True, timeout=60) as r:
                r.raise_for_status()
                
                # Get content length if available
                content_length = r.headers.get('content-length')
                if content_length:
                    self._total_bytes = int(content_length)
                
                with open(self.output_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=1024*64):
                        if self._stop_event.is_set():
                            break
                        if chunk: 
                            f.write(chunk)
                            f.flush()
                            with self._lock:
                                self._downloaded_bytes += len(chunk)
                                self._report_progress(self._downloaded_bytes)
                
                # Verify download completed
                if self._total_bytes > 0:
                    actual_size = self.output_path.stat().st_size
                    if actual_size < self._total_bytes:
                        raise ValueError(f"Download incomplete: Expected {self._total_bytes}, got {actual_size}")
        except Exception as e:
            raise e

    def _report_progress(self, current):
        if self.progress_callback and self._total_bytes > 0:
            percent = (current / self._total_bytes) * 100
            self.progress_callback(percent, current, self._total_bytes)

    def stop(self):
        """Stop the download."""
        self._stop_event.set()

