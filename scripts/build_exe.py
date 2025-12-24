#!/usr/bin/env python3
"""
Build script for VidFetch Windows executable using PyInstaller.

This script handles proper Tkinter data inclusion and PyInstaller configuration.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

try:
    import tomllib
except ImportError:
    # Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def get_version() -> str:
    """Get the current version from pyproject.toml."""
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"
    
    if tomllib is None:
        # Fallback: try to parse manually
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version ="):
                        version = line.split("=")[1].strip().strip('"').strip("'")
                        return version
        except Exception as e:
            print(f"Warning: Could not read version from pyproject.toml: {e}")
        return "0.0.0"
    
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception as e:
        print(f"Warning: Could not read version from pyproject.toml: {e}")
        return "0.0.0"


def build_exe(onefile: bool = True, debug: bool = False, console: bool = False):
    """Build the executable using PyInstaller."""
    project_root = Path(__file__).parent.parent
    app_path = project_root / "main.py"  # Use main.py which has absolute imports
    icon_path = project_root / "assets" / "logo.ico"
    
    # Get version
    version = get_version()
    print(f"Building VidFetch v{version}")
    print()
    
    if not app_path.exists():
        print(f"Error: App file not found: {app_path}")
        return False
    
    if not icon_path.exists():
        print(f"Warning: Icon file not found: {icon_path}")
        icon_path = None
    
    # Create releases directory structure
    releases_dir = project_root / "releases"
    version_dir = releases_dir / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Build PyInstaller command
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
    ]
    
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")
    
    if not console:
        # Hide console window (Windows only)
        cmd.append("--windowed")
        cmd.append("--noconsole")
    else:
        print("[DEBUG] Building with console enabled for debugging")
    
    # Icon
    if icon_path:
        cmd.append(f"--icon={icon_path}")
    
    # Include assets directory
    assets_dir = project_root / "assets"
    if assets_dir.exists():
        cmd.append(f"--add-data={assets_dir}{os.pathsep}assets")
    
    # Add src directory to Python path so imports work
    src_path = project_root / "src"
    cmd.append(f"--paths={src_path}")
    
    # Ensure yt-dlp and its dependencies are fully included
    # Collect all submodules for yt-dlp to avoid missing dependencies
    cmd.append("--collect-submodules=yt_dlp")
    cmd.append("--collect-submodules=requests")
    cmd.append("--collect-submodules=urllib3")
    
    # Hidden imports for modules that might not be auto-detected
    hidden_imports = [
        "yt_dlp.compat._legacy",
        "yt_dlp.compat._deprecated",
        "yt_dlp.utils._legacy",
        "yt_dlp.utils._deprecated",
        "mutagen",
        "brotli",
        "certifi",
        "secretstorage",
    ]
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")
    
    # Output name based on version
    exe_name = f"vidfetch-v{version}"
    cmd.append(f"--name={exe_name}")
    cmd.append(f"--distpath={project_root / 'build' / 'dist'}")
    cmd.append(f"--workpath={project_root / 'build'}")
    cmd.append(f"--specpath={project_root / 'build'}")
    
    # Clean build directory
    if not debug:
        cmd.append("--clean")
    
    # Main module - use main.py which has absolute imports
    cmd.append(str(app_path))
    
    print("Building with PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("\n[SUCCESS] Build completed successfully!")
        
        # Move executable to releases directory
        if onefile:
            source_exe = project_root / "build" / "dist" / f"{exe_name}.exe"
            target_exe = version_dir / f"{exe_name}.exe"
        else:
            source_exe = project_root / "build" / "dist" / exe_name / f"{exe_name}.exe"
            target_exe = version_dir / f"{exe_name}.exe"
            # For onedir, we might want to copy the whole directory
            source_dir = project_root / "build" / "dist" / exe_name
            target_dir = version_dir / exe_name
            if source_dir.exists():
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(source_dir, target_dir)
                print(f"Onedir package location: {target_dir}")
        
        if source_exe.exists():
            shutil.copy2(source_exe, target_exe)
            print(f"Executable location: {target_exe}")
            print(f"Release directory: {version_dir}")
            
            # Also create a latest symlink/copy for convenience
            latest_exe = releases_dir / f"{exe_name}.exe"
            if latest_exe.exists():
                latest_exe.unlink()
            shutil.copy2(target_exe, latest_exe)
            print(f"Latest build: {latest_exe}")
        else:
            print(f"Warning: Expected executable not found at {source_exe}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed with exit code {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Build interrupted by user")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build VidFetch executable with PyInstaller")
    parser.add_argument(
        "--no-onefile",
        action="store_true",
        help="Build as onedir directory instead of single executable"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output and keep build artifacts"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Keep console window for debugging (shows errors)"
    )
    args = parser.parse_args()
    
    success = build_exe(
        onefile=not args.no_onefile,
        debug=args.debug,
        console=args.console
    )
    
    sys.exit(0 if success else 1)

