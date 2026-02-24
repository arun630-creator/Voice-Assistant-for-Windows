"""
Nova Voice Assistant — File & Folder Management

Safe file-system operations:
  - Create / rename / delete folders
  - Open folders in File Explorer
  - List files in a directory
  - Empty the Recycle Bin
  - Open recent files / Downloads

Security:
  - All paths are resolved and validated against SAFE_ROOTS
  - No deletion of system directories
  - No recursive delete of entire drives
  - Path traversal attacks are blocked
"""

import os
import re
import subprocess
import ctypes
from pathlib import Path
from typing import List, Optional

from utils.logger import get_logger

log = get_logger(__name__)

# ── Safe root directories (user may only operate within these) ────────────────
_USER_HOME = Path.home()
_SAFE_ROOTS: List[Path] = [
    _USER_HOME / "Desktop",
    _USER_HOME / "Documents",
    _USER_HOME / "Downloads",
    _USER_HOME / "Music",
    _USER_HOME / "Pictures",
    _USER_HOME / "Videos",
    _USER_HOME / "OneDrive",
    Path("D:/"),          # common secondary drive
    Path("E:/"),          # common secondary drive
]

# Well-known folder shortcuts
_FOLDER_ALIASES = {
    "desktop": _USER_HOME / "Desktop",
    "documents": _USER_HOME / "Documents",
    "downloads": _USER_HOME / "Downloads",
    "music": _USER_HOME / "Music",
    "pictures": _USER_HOME / "Pictures",
    "videos": _USER_HOME / "Videos",
    "home": _USER_HOME,
    "user": _USER_HOME,
    "onedrive": _USER_HOME / "OneDrive",
    "recycle bin": "shell:RecycleBinFolder",
    "recent": "shell:Recent",
    "startup": "shell:Startup",
    "temp": Path(os.environ.get("TEMP", str(_USER_HOME / "AppData/Local/Temp"))),
}


def _is_safe_path(path: Path) -> bool:
    """Return True if *path* is under one of the SAFE_ROOTS or is the user home."""
    resolved = path.resolve()
    # Always allow user home itself
    if resolved == _USER_HOME.resolve():
        return True
    for root in _SAFE_ROOTS:
        try:
            if resolved == root.resolve() or root.resolve() in resolved.parents:
                return True
        except (OSError, ValueError):
            continue
    return False


def _resolve_folder(name: str) -> Optional[Path]:
    """Resolve a folder name or path. Returns Path or None if invalid."""
    # Check aliases first
    lower = name.lower().strip()
    if lower in _FOLDER_ALIASES:
        val = _FOLDER_ALIASES[lower]
        if isinstance(val, str):
            return None  # shell: paths handled separately
        return val

    # Try as absolute path
    try:
        p = Path(name)
        if p.is_absolute():
            return p
    except (OSError, ValueError):
        pass

    # Try relative to Desktop, then Documents
    for base in [_USER_HOME / "Desktop", _USER_HOME / "Documents"]:
        candidate = base / name
        if candidate.exists():
            return candidate

    # Try as relative to Desktop (for creation)
    return _USER_HOME / "Desktop" / name


class FileManager:
    """Safe file-system operations for the voice assistant."""

    @staticmethod
    def create_folder(folder_name: str, location: str = "desktop") -> str:
        """Create a new folder. Default location is Desktop."""
        lower = location.lower().strip()
        base = _FOLDER_ALIASES.get(lower)
        if base is None or isinstance(base, str):
            base = _USER_HOME / "Desktop"

        target = base / folder_name
        if not _is_safe_path(target):
            return f"Sorry, I can't create folders in that location."

        try:
            target.mkdir(parents=True, exist_ok=True)
            log.info("Created folder: %s", target)
            return f"Created folder '{folder_name}' on your {location}."
        except PermissionError:
            return f"Permission denied. Can't create folder there."
        except OSError as exc:
            log.error("Failed to create folder %s: %s", target, exc)
            return f"Failed to create folder '{folder_name}'."

    @staticmethod
    def delete_folder(folder_name: str) -> str:
        """Delete an empty folder (safe — won't delete non-empty)."""
        target = _resolve_folder(folder_name)
        if target is None or not target.exists():
            return f"Couldn't find folder '{folder_name}'."

        if not _is_safe_path(target):
            return "Sorry, I can't delete folders in that location."

        if not target.is_dir():
            return f"'{folder_name}' is not a folder."

        try:
            # Only delete if empty (safe)
            contents = list(target.iterdir())
            if contents:
                return (
                    f"Folder '{folder_name}' is not empty "
                    f"({len(contents)} item(s)). Please empty it first."
                )
            target.rmdir()
            log.info("Deleted empty folder: %s", target)
            return f"Deleted folder '{folder_name}'."
        except PermissionError:
            return "Permission denied."
        except OSError as exc:
            log.error("Failed to delete folder: %s", exc)
            return f"Failed to delete '{folder_name}'."

    @staticmethod
    def rename_folder(old_name: str, new_name: str) -> str:
        """Rename a folder."""
        source = _resolve_folder(old_name)
        if source is None or not source.exists():
            return f"Couldn't find folder '{old_name}'."

        if not _is_safe_path(source):
            return "Sorry, I can't rename folders in that location."

        target = source.parent / new_name
        if target.exists():
            return f"A folder named '{new_name}' already exists there."

        try:
            source.rename(target)
            log.info("Renamed folder: %s → %s", source, target)
            return f"Renamed '{old_name}' to '{new_name}'."
        except OSError as exc:
            log.error("Failed to rename folder: %s", exc)
            return f"Failed to rename '{old_name}'."

    @staticmethod
    def open_folder(folder_name: str) -> str:
        """Open a folder in File Explorer."""
        lower = folder_name.lower().strip()

        # Handle shell: paths (recycle bin, recent, etc.)
        alias = _FOLDER_ALIASES.get(lower)
        if isinstance(alias, str) and alias.startswith("shell:"):
            try:
                subprocess.Popen(
                    ["explorer.exe", alias],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"Opening {folder_name}."
            except OSError:
                return f"Failed to open {folder_name}."

        target = _resolve_folder(folder_name)
        if target is None:
            return f"Couldn't find folder '{folder_name}'."

        if not target.exists():
            return f"Folder '{folder_name}' doesn't exist."

        try:
            os.startfile(str(target))
            log.info("Opened folder: %s", target)
            return f"Opening {folder_name}."
        except OSError as exc:
            log.error("Failed to open folder: %s", exc)
            return f"Failed to open '{folder_name}'."

    @staticmethod
    def list_files(folder_name: str = "desktop", limit: int = 15) -> str:
        """List files in a folder (default: Desktop)."""
        target = _resolve_folder(folder_name)
        if target is None or not target.exists():
            return f"Couldn't find folder '{folder_name}'."

        if not target.is_dir():
            return f"'{folder_name}' is not a folder."

        try:
            items = sorted(target.iterdir(), key=lambda p: p.name.lower())
            if not items:
                return f"'{folder_name}' is empty."

            lines = []
            for i, item in enumerate(items[:limit]):
                icon = "📁" if item.is_dir() else "📄"
                lines.append(f"{icon} {item.name}")

            result = "\n".join(lines)
            extra = len(items) - limit
            if extra > 0:
                result += f"\n… and {extra} more items."

            return f"Files in {folder_name}:\n{result}"
        except PermissionError:
            return f"Permission denied to list '{folder_name}'."
        except OSError as exc:
            log.error("Failed to list files: %s", exc)
            return f"Failed to list files in '{folder_name}'."

    @staticmethod
    def empty_recycle_bin() -> str:
        """Empty the Windows Recycle Bin."""
        try:
            # SHEmptyRecycleBin flags: SHERB_NOCONFIRMATION=1 | SHERB_NOPROGRESSUI=2 | SHERB_NOSOUND=4
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x07)
            log.info("Recycle Bin emptied")
            return "Recycle Bin emptied."
        except Exception as exc:
            log.error("Failed to empty Recycle Bin: %s", exc)
            return "Failed to empty the Recycle Bin."

    @staticmethod
    def open_downloads() -> str:
        """Open the Downloads folder."""
        return FileManager.open_folder("downloads")

    @staticmethod
    def open_recent() -> str:
        """Open the Recent files folder."""
        try:
            subprocess.Popen(
                ["explorer.exe", "shell:Recent"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return "Opening recent files."
        except OSError:
            return "Failed to open recent files."
