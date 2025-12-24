"""Version management for VidFetch."""

from pathlib import Path

try:
    import tomllib
except ImportError:
    # Python < 3.11 fallback
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None


def get_version() -> str:
    """Get the current version from pyproject.toml."""
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"
    
    if tomllib is None:
        # Fallback: try to parse manually
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version ="):
                        version = line.split("=")[1].strip().strip('"').strip("'")
                        return version
        except Exception:
            pass
        return "0.0.0"
    
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        # Fallback version if we can't read it
        return "0.0.0"


__version__ = get_version()

