# VidFetch

A modern, cross-platform YouTube video downloader with a beautiful GUI built using CustomTkinter. Download videos and playlists in various formats and quality options with an intuitive interface.

![VidFetch](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

- 🎥 **Single Video Downloads** - Download individual YouTube videos in your preferred format and quality
- 📚 **Playlist Support** - Download entire playlists with selective video selection
- 🎨 **Modern UI** - Beautiful, dark-themed interface built with CustomTkinter
- 📊 **Multiple Formats** - Support for MP4, WebM, and MKV formats
- 🎯 **Quality Selection** - Choose from available resolutions (360p, 720p, 1080p, etc.)
- 📥 **Smart Downloading** - Robust multi-threaded downloads with progress tracking
- 🔄 **Audio/Video Muxing** - Automatic merging of separate video and audio streams using FFmpeg
- 📋 **Download Management** - Track and manage multiple downloads simultaneously
- 🖼️ **Thumbnail Preview** - View video thumbnails before downloading
- ⚡ **Fast & Reliable** - Optimized download engine with retry logic and error handling

## 🖼️ Screenshots

*Screenshots coming soon*

## 🚀 Installation

### Prerequisites

- Python 3.12 or higher
- [FFmpeg](https://ffmpeg.org/download.html) (required for video/audio muxing)
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Install FFmpeg

**Windows:**
- Download from [FFmpeg website](https://ffmpeg.org/download.html)
- Add FFmpeg to your system PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg  # Debian/Ubuntu
sudo yum install ffmpeg      # CentOS/RHEL
```

### Install VidFetch

**Using uv (recommended):**
```bash
# Clone the repository
git clone https://github.com/yourusername/vidfetch.git
cd vidfetch

# Install dependencies
uv sync

# Run the application
uv run python -m src.vidfetch.app
```

**Using pip:**
```bash
# Clone the repository
git clone https://github.com/yourusername/vidfetch.git
cd vidfetch

# Install dependencies
pip install -e .

# Run the application
python -m src.vidfetch.app
```

## 📖 Usage

1. **Launch VidFetch** - Start the application
2. **Paste URL** - Enter a YouTube video or playlist URL in the search bar
3. **Select Quality** - Choose your preferred format and quality from the available options
4. **Download** - Click the download button and select your save location
5. **Monitor Progress** - Track your downloads in the Downloads tab

### Supported URL Formats

- Single video: `https://www.youtube.com/watch?v=VIDEO_ID`
- Playlist: `https://www.youtube.com/playlist?list=PLAYLIST_ID`
- Short URL: `https://youtu.be/VIDEO_ID`

## 🛠️ Building Executable

Build a standalone executable for Windows:

```bash
# Using the build script
python scripts/build_exe.py

# Or manually with PyInstaller
pyinstaller --onefile --windowed --icon=assets/logo.ico --name=vidfetch main.py
```

The executable will be created in the `build/dist/` directory.

## 🏗️ Project Structure

```
vidfetch/
├── src/
│   └── vidfetch/
│       ├── core/           # Core functionality
│       │   ├── downloader.py    # Smart downloader with multi-threading
│       │   ├── muxer.py         # FFmpeg video/audio muxing
│       │   ├── youtube_client.py # YouTube metadata extraction
│       │   └── models.py        # Data models
│       ├── ui/             # User interface
│       │   ├── main_window.py   # Main application window
│       │   ├── download_item.py # Download item component
│       │   └── components.py    # UI components
│       ├── utils/          # Utilities
│       │   ├── config.py        # Configuration management
│       │   ├── paths.py         # Path utilities
│       │   └── logging.py       # Logging setup
│       └── app.py          # Application entry point
├── assets/                 # Application assets
├── scripts/                # Build and utility scripts
└── tests/                  # Test files
```

## 🧪 Technologies

- **CustomTkinter** - Modern, customizable Tkinter widgets
- **yt-dlp** - YouTube video metadata and URL extraction
- **FFmpeg** - Video/audio processing and muxing
- **Pillow (PIL)** - Image processing for thumbnails
- **requests** - HTTP library for downloads
- **Python 3.12+** - Modern Python features

## 🐛 Known Issues

- MP4 downloads may require special handling for YouTube URLs (single-threaded downloads)
- Some videos may not have all quality options available
- Playlist downloads may take longer for large playlists

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - For YouTube video extraction
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - For the beautiful UI framework
- [FFmpeg](https://ffmpeg.org/) - For video/audio processing

## 📧 Contact

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Note:** This project is for educational purposes. Please respect YouTube's Terms of Service and copyright laws when downloading content.

