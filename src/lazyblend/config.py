"""Application configuration management."""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path.home() / ".config" / "lazyblend"
CONFIG_FILE = CONFIG_DIR / "config.json"
FAVORITES_FILE = CONFIG_DIR / "favorites.json"
RECENT_FILE = CONFIG_DIR / "recent.json"

DEFAULT_SCAN_DIRS = [
    str(Path.home() / "Documents"),
    str(Path.home() / "Projects"),
    str(Path.home() / "Desktop"),
    str(Path.home()),
]


@dataclass
class Config:
    scan_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_SCAN_DIRS))
    blender_path: str = "blender"
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
