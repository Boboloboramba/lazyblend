"""Application configuration management."""

import json
import shutil
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path.home() / ".config" / "lazyblend"
CONFIG_FILE = CONFIG_DIR / "config.json"
FAVORITES_FILE = CONFIG_DIR / "favorites.json"
RECENT_FILE = CONFIG_DIR / "recent.json"
CACHE_DIR = CONFIG_DIR / "cache"

DEFAULT_SCAN_DIRS = [
    str(Path.home() / "Documents"),
    str(Path.home() / "Projects"),
    str(Path.home() / "Desktop"),
    str(Path.home()),
]


def find_blender() -> str:
    """Auto-detect Blender executable path."""
    # Check PATH first
    path = shutil.which("blender")
    if path:
        return path

    # macOS standard install location
    if sys.platform == "darwin":
        mac_paths = [
            "/Applications/Blender.app/Contents/MacOS/blender",
            str(Path.home() / "Applications" / "Blender.app" / "Contents" / "MacOS" / "blender"),
        ]
        for p in mac_paths:
            if Path(p).exists():
                return p

    # Windows standard install location
    if sys.platform == "win32":
        win_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        ]
        for p in win_paths:
            if Path(p).exists():
                return p

    # Linux Flatpak
    flatpak = shutil.which("flatpak")
    if flatpak:
        import subprocess
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True, text=True, timeout=5
            )
            if "org.blender.Blender" in result.stdout:
                return "flatpak run org.blender.Blender"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return "blender"


@dataclass
class Config:
    scan_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_SCAN_DIRS))
    blender_path: str = field(default_factory=find_blender)
    max_recent: int = 50
    show_hidden: bool = False
    sort_by: str = "name"  # name, size, date
    sort_reverse: bool = False

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()


def load_favorites() -> list[str]:
    if FAVORITES_FILE.exists():
        try:
            return json.loads(FAVORITES_FILE.read_text())
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def save_favorites(favs: list[str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    FAVORITES_FILE.write_text(json.dumps(favs, indent=2))


def load_recent() -> list[str]:
    if RECENT_FILE.exists():
        try:
            return json.loads(RECENT_FILE.read_text())
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def save_recent(recent: list[str], max_items: int = 50) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    RECENT_FILE.write_text(json.dumps(recent[:max_items], indent=2))
