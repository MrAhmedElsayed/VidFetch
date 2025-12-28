# VidFetch

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/yourusername/vidfetch)
[![Python](https://img.shields.io/badge/python-3.12+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)

VidFetch is a sophisticated, cross-platform application designed for the efficient downloading of YouTube videos and playlists. Engineered with a focus on user experience and performance, VidFetch leverages a modern GUI built on CustomTkinter to provide a seamless interaction model. It supports a wide array of formats and quality resolutions, ensuring versatility for all user requirements.

## 📋 Table of Contents

- [Key Features](#-key-features)
- [System Requirements](#-system-requirements)
- [Installation Guide](#-installation-guide)
- [Operational Usage](#-operational-usage)
- [Technical Architecture](#-technical-architecture)
- [Contributing](#-contributing)
- [License](#-license)
- [Disclaimer](#-disclaimer)

## ✨ Key Features

- **High-Fidelity Downloads**: download individual videos in customizable formats (MP4, WebM, MKV) and resolutions ranging from 360p to 4K.
- **Playlist Management**: Comprehensive support for downloading entire playlists with selective filtering capabilities.
- **Modern User Interface**: A polished, dark-themed interface developed using CustomTkinter, prioritizing accessibility and aesthetic appeal.
- **Intelligent Processing**: Robust multi-threaded download engine with built-in retry logic, progress tracking, and error handling.
- **Media Muxing**: seamless integration with FFmpeg for automatic merging of high-quality video and audio streams.
- **Download Management**: specialized tab for monitoring multiple concurrent downloads with real-time status updates.
- **Visual Previews**: integrated thumbnail viewer for immediate content verification prior to download.

## 💻 System Requirements

To ensure optimal performance, the following prerequisites must be met:

- **Operating System**: Windows 10/11, macOS 11+, or modern Linux distributions.
- **Python**: Version 3.12 or higher.
- **External Dependencies**:
    - [FFmpeg](https://ffmpeg.org/download.html) (Essential for video/audio muxing).

## 🚀 Installation Guide

### 1. Install FFmpeg

VidFetch requires FFmpeg for processing media files. Please install it based on your operating system:

*   **Windows**: Download from the [official website](https://ffmpeg.org/download.html) and add to system PATH.
*   **macOS**:
    ```bash
    brew install ffmpeg
    ```
*   **Linux (Debian/Ubuntu)**:
    ```bash
    sudo apt-get install ffmpeg
    ```

### 2. Install VidFetch

We recommend using `uv` for dependency management, though `pip` is fully supported.

#### Option A: Using `uv` (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/vidfetch.git
cd vidfetch

# Sync dependencies
uv sync

# Launch application
uv run python -m src.vidfetch.app
```

#### Option B: Using `pip`

```bash
# Clone the repository
git clone https://github.com/yourusername/vidfetch.git
cd vidfetch

# Install in editable mode
pip install -e .

# Launch application
python -m src.vidfetch.app
```

## 📖 Operational Usage

1.  **Initialization**: Launch the application via the command line interface.
2.  **Input Configuration**: Navigate to the "Home" tab and input a valid YouTube URL (Video or Playlist).
3.  **Parameter Selection**: Select the desired file format (e.g., MP4) and resolution quality from the dropdown menus.
4.  **Execution**: Initiate the process by clicking the "Download" button. You will be prompted to select a destination directory.
5.  **Monitoring**: Switch to the "Downloads" tab to view real-time progress, speed, and completion status.

### Supported URL Formats

*   **Standard Video**: `https://www.youtube.com/watch?v=VIDEO_ID`
*   **Playlist**: `https://www.youtube.com/playlist?list=PLAYLIST_ID`
*   **Shortened**: `https://youtu.be/VIDEO_ID`

## 🛠️ Building Executable

To generate a standalone executable for distribution, utilize the provided build scripts:

```bash
# Automated build script
python scripts/build_exe.py

# Manual PyInstaller command
pyinstaller --onefile --windowed --icon=assets/logo.ico --name=vidfetch main.py
```
*The output artifact will be located in the `build/dist/` directory.*

## 🏗️ Technical Architecture

VidFetch is structured to promote modularity and maintainability:

```text
vidfetch/
├── src/vidfetch/
│   ├── core/           # Business logic: Downloader, Muxer, YouTube Client
│   ├── ui/             # Presentation layer: MainWindow, Components
│   └── utils/          # Shared utilities: Config, Logging, Paths
├── assets/             # Static resources
└── scripts/            # DevOps and build automation
```

### Technical Stack

-   **GUI Framework**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
-   **Core Engine**: [yt-dlp](https://github.com/yt-dlp/yt-dlp)
-   **Media Processing**: FFmpeg
-   **Network**: requests
-   **Image Processing**: Pillow

## 🤝 Contributing

We welcome contributions from the community. To contribute:

1.  Fork the project.
2.  Create a feature branch (`git checkout -b feature/NewFeature`).
3.  Commit your changes (`git commit -m 'Implement NewFeature'`).
4.  Push to the branch (`git push origin feature/NewFeature`).
5.  Open a Pull Request.

Please ensure all new code adheres to the project's coding standards and includes appropriate tests.

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.

## ⚠️ Disclaimer

This application is intended for educational and personal archiving purposes only. Users are responsible for complying with YouTube's Terms of Service and applicable copyright laws in their jurisdiction. The developers of VidFetch assume no liability for misuse of this software.

