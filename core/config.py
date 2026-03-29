"""
OpenPriors Configuration

Local-first config stored at ~/.openpriors/config.json.
Users bring their own API keys (BYOK).
"""

import json
import os
from pathlib import Path
from typing import Optional

OPENPRIORS_HOME = Path(os.environ.get("OPENPRIORS_HOME", Path.home() / ".openpriors"))
CONFIG_FILE = OPENPRIORS_HOME / "config.json"
PRIORS_DIR = OPENPRIORS_HOME / "priors"
DB_PATH = OPENPRIORS_HOME / "openpriors.db"

DEFAULT_CONFIG = {
    "llm": {
        "provider": "gemini",
        "model": "gemini/gemini-2.5-flash",
        "api_key": None,
    },
    "storage": {
        "priors_dir": str(PRIORS_DIR),
        "db_path": str(DB_PATH),
    },
}


def ensure_dirs():
    OPENPRIORS_HOME.mkdir(parents=True, exist_ok=True)
    PRIORS_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_api_key(provider: Optional[str] = None) -> Optional[str]:
    """Get API key from config or environment variables."""
    config = load_config()
    key = config.get("llm", {}).get("api_key")
    if key:
        return key

    # Fallback to env vars
    provider = provider or config.get("llm", {}).get("provider", "gemini")
    env_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var:
        return os.environ.get(env_var)
    return None


def get_model() -> str:
    config = load_config()
    return config.get("llm", {}).get("model", "gemini/gemini-2.5-flash")


def get_priors_dir() -> Path:
    config = load_config()
    return Path(config.get("storage", {}).get("priors_dir", str(PRIORS_DIR)))


def get_db_path() -> Path:
    config = load_config()
    return Path(config.get("storage", {}).get("db_path", str(DB_PATH)))
