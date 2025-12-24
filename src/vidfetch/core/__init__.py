"""Core functionality for VidFetch."""

from .models import (
    VideoFormat,
    VideoMetadata,
    PlaylistEntry,
    PlaylistMetadata,
)
from .youtube_client import YouTubeClient
from .downloader import SmartDownloader
from .muxer import MediaMuxer

__all__ = [
    "VideoFormat",
    "VideoMetadata",
    "PlaylistEntry",
    "PlaylistMetadata",
    "YouTubeClient",
    "SmartDownloader",
    "MediaMuxer",
]

