"""Data models for video and playlist metadata."""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class VideoFormat:
    """Represents a video format/stream."""
    format_id: str
    ext: str
    resolution: str  # e.g., "1920x1080"
    note: str        # e.g., "1080p"
    filesize: int
    url: str
    vcodec: str
    acodec: str
    fps: float
    is_video_only: bool
    http_headers: Optional[Dict[str, str]] = None
    language: Optional[str] = None


@dataclass
class VideoMetadata:
    """Metadata for a single video."""
    title: str
    duration: int
    thumbnail_url: str
    formats: List[VideoFormat]
    original_url: str


@dataclass
class PlaylistEntry:
    """A single entry in a playlist."""
    title: str
    url: str
    duration: int


@dataclass
class PlaylistMetadata:
    """Metadata for a playlist."""
    title: str
    entries: List[PlaylistEntry]
    original_url: str

