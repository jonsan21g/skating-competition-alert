"""Configuration management for skating-competition-alert."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"
WATCHLIST_FILE = CONFIG_DIR / "watchlist.json"
SOURCES_FILE = CONFIG_DIR / "sources.json"
ENV_FILE = PROJECT_ROOT / ".env"


def load_env_file(filepath: Path = ENV_FILE) -> None:
    """Simple, dependency-free .env file parser."""
    if not filepath.exists():
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    # Do not overwrite existing environment variables
                    if key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        print(f"Warning: Failed to read {filepath}: {e}")


# Load environment variables on module import
load_env_file()


def load_watchlist() -> Dict[str, Any]:
    """Loads watchlist.json configuration."""
    if not WATCHLIST_FILE.exists():
        return {
            "global_settings": {
                "warn_low_spots_threshold": 5,
                "check_interval_seconds": 300,
            },
            "watched_competitions": [],
        }
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_watchlist(data: Dict[str, Any]) -> None:
    """Saves updated watchlist to JSON."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_sources() -> Dict[str, Any]:
    """Loads sources.json configuration defining scrape URLs."""
    if not SOURCES_FILE.exists():
        return {"sources": []}
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class AppConfig:
    """Unified application settings (WhatsApp via CallMeBot + Console)."""

    # Notification settings
    NOTIFIERS_ENABLED: List[str] = [
        n.strip().lower()
        for n in os.getenv("NOTIFIERS_ENABLED", "console,whatsapp").split(",")
        if n.strip()
    ]

    # WhatsApp (CallMeBot)
    CALLMEBOT_PHONE: str = os.getenv("CALLMEBOT_PHONE", "").strip()
    CALLMEBOT_API_KEY: str = os.getenv("CALLMEBOT_API_KEY", "").strip()

    # Scraper & Daemon settings
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
