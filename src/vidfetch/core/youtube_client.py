"""YouTube metadata extraction using yt-dlp."""

from typing import Union
import yt_dlp

from .models import VideoMetadata, PlaylistMetadata, PlaylistEntry, VideoFormat


class YouTubeClient:
    """Handles interaction with YouTube to extract metadata."""
    
    def __init__(self):
        self._ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'dump_single_json': True,
            'extract_flat': 'in_playlist',  # Extract playlist entries without downloading their full info immediately
        }

    def get_video_info(self, url: str) -> Union[VideoMetadata, PlaylistMetadata]:
        """Extracts video metadata and formats."""
        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                raise ValueError(f"Failed to fetch metadata: {str(e)}")

            if 'entries' in info:
                # It's a playlist
                entries = []
                for e in info['entries']:
                    if not e:
                        continue
                    entries.append(PlaylistEntry(
                        title=e.get('title', 'Unknown'),
                        url=e.get('url') or e.get('webpage_url'),
                        duration=e.get('duration', 0)
                    ))
                
                return PlaylistMetadata(
                    title=info.get('title', 'Unknown Playlist'),
                    entries=entries,
                    original_url=url
                )

            # Single Video Processing
            formats = []
            
            for f in info.get('formats', []):
                is_video = f.get('vcodec') != 'none'
                is_audio = f.get('acodec') != 'none'
                
                if not is_video and not is_audio:
                    continue

                fmt = VideoFormat(
                    format_id=f.get('format_id'),
                    ext=f.get('ext'),
                    resolution=f"{f.get('width')}x{f.get('height')}" if f.get('width') else "N/A",
                    note=f.get('format_note', ''),
                    filesize=f.get('filesize') or f.get('filesize_approx') or 0,
                    url=f.get('url'),
                    vcodec=f.get('vcodec'),
                    acodec=f.get('acodec'),
                    fps=f.get('fps') or 0,
                    is_video_only=(is_video and not is_audio),
                    http_headers=f.get('http_headers'),
                    language=f.get('language')
                )

                formats.append(fmt)

            return VideoMetadata(
                title=info.get('title', 'Unknown Title'),
                duration=info.get('duration', 0),
                thumbnail_url=info.get('thumbnail', ''),
                formats=formats,
                original_url=url
            )

