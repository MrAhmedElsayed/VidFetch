#!/usr/bin/env python3
"""
Diagnostic script to test PyInstaller build and identify issues.

This helps diagnose why the .exe might not be launching.
"""

import subprocess
import sys
from pathlib import Path


def test_onedir_first():
    """Test onedir build (not onefile) first to isolate issues."""
    project_root = Path(__file__).parent.parent
    app_path = project_root / "src" / "vidfetch" / "app.py"
    icon_path = project_root / "assets" / "logo.ico"
    
    print("=" * 60)
    print("Testing ONEDIR build (not onefile)")
    print("This helps isolate if the issue is with onefile mode")
    print("=" * 60)
    print()
    
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--onedir",
        "--windowed",
        "--noconsole",
        f"--icon={icon_path}" if icon_path.exists() else "",
        f"--name=app_onedir",
        f"--distpath={project_root}",
        str(app_path),
    ]
    
    # Remove empty strings
    cmd = [c for c in cmd if c]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
        exe_path = project_root / "app_onedir" / "app_onedir.exe"
        if exe_path.exists():
            print(f"\n✓ Onedir build created: {exe_path}")
            print(f"  Try running: {exe_path}")
            return True
        else:
            print(f"\n✗ Build completed but exe not found at: {exe_path}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    print("=" * 60)
    print("Checking dependencies...")
    print("=" * 60)
    print()
    
    checks = {
        "Python": sys.executable,
        "PyInstaller": None,
        "Tkinter": None,
        "Tcl/Tk DLLs": None,
    }
    
    # Check PyInstaller
    try:
        import PyInstaller
        checks["PyInstaller"] = f"✓ {PyInstaller.__version__}"
    except ImportError:
        checks["PyInstaller"] = "✗ Not installed"
    
    # Check Tkinter
    try:
        import tkinter
        checks["Tkinter"] = f"✓ {tkinter.__file__}"
        
        # Check Tcl/Tk DLLs
        import os
        python_base = Path(sys.executable).parent
        tcl_dll = python_base / "DLLs" / "tcl86t.dll"
        tk_dll = python_base / "DLLs" / "tk86t.dll"
        
        if tcl_dll.exists() and tk_dll.exists():
            checks["Tcl/Tk DLLs"] = f"✓ Found: {tcl_dll.name}, {tk_dll.name}"
        else:
            checks["Tcl/Tk DLLs"] = f"✗ Not found in {python_base / 'DLLs'}"
    except ImportError:
        checks["Tkinter"] = "✗ Not available"
    
    for name, status in checks.items():
        print(f"{name:15} {status}")
    
    print()
    return all("✓" in str(v) or v is None for v in checks.values())


if __name__ == "__main__":
    print("\nVidFetch Build Diagnostics\n")
    
    if not check_dependencies():
        print("⚠ Some dependencies are missing. Fix these first.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    response = input("Test onedir build first? (y/n): ").strip().lower()
    if response == 'y':
        test_onedir_first()
    else:
        print("Skipping onedir test. Run build_exe.py instead.")

