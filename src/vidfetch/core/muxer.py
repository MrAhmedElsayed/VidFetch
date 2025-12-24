"""Media muxing using FFmpeg."""

import os
import subprocess
from pathlib import Path


class MediaMuxer:
    """Merges video and audio streams using FFmpeg."""
    
    @staticmethod
    def merge(video_path: Path, audio_path: Path, output_path: Path):
        """Merges video and audio. Requires ffmpeg in system PATH."""
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if files exist and have content
        if not video_path.exists() or video_path.stat().st_size == 0:
            raise RuntimeError(f"Video file is missing or empty: {video_path}")
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError(f"Audio file is missing or empty: {audio_path}")

        # Determine output format and appropriate codec
        output_ext = output_path.suffix.lower()
        
        # Detect actual format of input files (may differ from extension)
        # Use ffprobe to detect format, or infer from extension
        video_ext = video_path.suffix.lower()
        audio_ext = audio_path.suffix.lower()
        
        # WebM only supports VP8/VP9/AV1 video and Vorbis/Opus audio
        # MP4 supports H.264/H.265 video and AAC audio
        if output_ext == '.webm' or video_ext == '.webm':
            # For WebM, keep opus audio (don't convert to aac)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-i', str(audio_path),
                '-c:v', 'copy',  # Copy video stream
                '-c:a', 'copy',  # Copy audio stream (keep opus for webm)
                str(output_path)
            ]
        else:
            # For MP4/MKV, use AAC audio
            # Auto-detect input formats, convert audio to AAC
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-i', str(audio_path),
                '-c:v', 'copy',  # Copy video stream (fast)
                '-c:a', 'aac',   # Re-encode audio to AAC for compatibility
                '-b:a', '192k',  # Set audio bitrate
                '-movflags', '+faststart',  # Optimize for streaming
                str(output_path)
            ]

        # On Windows, prevent console window popping up
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode('utf-8', errors='ignore')}")
                
        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg and add it to your PATH.")

