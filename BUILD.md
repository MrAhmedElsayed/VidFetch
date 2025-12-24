# VidFetch Build Guide

## Building Windows Executable with PyInstaller

This guide covers building VidFetch as a Windows `.exe` using PyInstaller.

## Quick Start

### Using the Build Script (Recommended)

```bash
# Build onefile executable (default)
uv run python scripts/build_exe.py

# Build onedir directory (easier to debug)
uv run python scripts/build_exe.py --no-onefile

# Build with console for debugging
uv run python scripts/build_exe.py --console

# Build with debug output
uv run python scripts/build_exe.py --debug
```

### Manual Build Command

```bash
uv run python -m PyInstaller \
  --onefile \
  --windowed \
  --noconsole \
  --icon=assets/logo.ico \
  --add-data=assets;assets \
  --name=app \
  src/vidfetch/app.py
```

## Common Issues and Solutions

### Issue: `.exe` doesn't launch / silent failure

**Symptoms:**
- Double-clicking the `.exe` does nothing
- No error message appears
- No window opens

**Diagnosis Steps:**

1. **Build with console enabled** to see errors:
   ```bash
   uv run python scripts/build_exe.py --console
   ```
   Then run `app.exe` from command line to see error messages.

2. **Check error log**:
   The app logs errors to `%USERPROFILE%\vidfetch_error.log` if it fails to start.

3. **Test onedir build first**:
   ```bash
   uv run python scripts/build_exe.py --no-onefile
   ```
   Then run `app\app.exe`. If this works, the issue is with onefile mode.

**Common Causes:**

1. **Missing Tcl/Tk data files**: PyInstaller needs to include Tcl/Tk runtime data.
   - **Solution**: PyInstaller should auto-detect these, but you may need to add them manually with `--collect-all tkinter`.

2. **Missing DLLs**: Tkinter requires `tcl86t.dll` and `tk86t.dll`.
   - **Solution**: PyInstaller should auto-detect these, but ensure they're in your Python installation.

3. **Path resolution issues**: Resource paths might not resolve correctly in onefile mode.
   - **Solution**: The `resource_path()` function in `app.py` handles this using `sys._MEIPASS`.

4. **Silent exceptions**: Unhandled exceptions in GUI apps can cause silent failures.
   - **Solution**: Error logging is now included in `app.py`.

### Issue: Icon not showing

- Ensure `assets/logo.ico` exists
- Verify the icon file is valid (try opening it)
- Check build output for icon-related warnings

### Issue: Build fails

- Check that all dependencies are installed: `uv sync`
- Ensure PyInstaller is installed: `uv add pyinstaller`
- Try building with `--debug` flag for more information

## Build Modes

### Onefile Mode (Default)
- Single `.exe` file
- Slower startup (extracts to temp directory)
- Easier distribution
- Use: `--onefile`

### Onedir Mode
- Directory with `.exe` and dependencies
- Faster startup
- Easier to debug
- Use: `--no-onefile` (uses `--onedir`)

## File Locations

- **Onefile output**: `app.exe` (project root)
- **Onedir output**: `app/app.exe` (in project root)
- **Build artifacts**: `build/`, `.spec` files (cleaned up unless `--debug`)

## Testing the Build

1. **Test onedir first** (recommended):
   ```bash
   uv run python scripts/build_exe.py --no-onefile
   cd app
   .\app.exe
   ```

2. **If onedir works, test onefile**:
   ```bash
   uv run python scripts/build_exe.py
   .\app.exe
   ```

3. **If onefile fails, use console mode**:
   ```bash
   uv run python scripts/build_exe.py --console
   .\app.exe
   ```
   (Run from command line to see errors)

## Troubleshooting Checklist

- [ ] Python 3.12+ installed
- [ ] PyInstaller installed: `uv add pyinstaller`
- [ ] Tkinter works: `python -c "import tkinter; tkinter._test()"`
- [ ] Icon file exists: `assets/logo.ico`
- [ ] Build completes without errors
- [ ] Tested onedir build first
- [ ] Checked error log: `%USERPROFILE%\vidfetch_error.log`
- [ ] Built with `--console` to see errors

## Next Steps

Once the minimal build works:
1. Add more features to the app
2. Test on clean Windows machines
3. Set up CI/CD for automated builds
4. Consider code signing for distribution
