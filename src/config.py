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
                "alert_on_any_new_open": True,
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


class AppConfig:
    """Unified application settings."""

    # Notification settings
    NOTIFIERS_ENABLED: List[str] = [
        n.strip().lower()
        for n in os.getenv("NOTIFIERS_ENABLED", "console").split(",")
        if n.strip()
    ]

    # WhatsApp (CallMeBot)
    CALLMEBOT_PHONE: str = os.getenv("CALLMEBOT_PHONE", "").strip()
    CALLMEBOT_API_KEY: str = os.getenv("CALLMEBOT_API_KEY", "").strip()

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    # Discord
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    # Email
    EMAIL_SMTP_HOST: str = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com").strip()
    EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    EMAIL_SMTP_USER: str = os.getenv("EMAIL_SMTP_USER", "").strip()
    EMAIL_SMTP_PASSWORD: str = os.getenv("EMAIL_SMTP_PASSWORD", "").strip()
    EMAIL_TO: str = os.getenv("EMAIL_TO", "").strip()

    # Scraper & Daemon settings
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
    ALERT_ON_ANY_NEW_COMPETITION: bool = os.getenv(
        "ALERT_ON_ANY_NEW_COMPETITION", "true"
    ).lower() in ("true", "1", "yes")

    # DSU URL
    DSU_OVERVIEW_LIST_URL: str = "https://dsu.klub-modul.dk/cms/EventOverviewList.aspx"
    DSU_BASE_URL: str = "https://dsu.klub-modul.dk/cms/"
