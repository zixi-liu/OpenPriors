"""Slack bot configuration — loads tokens from config file or env vars."""

import os
from dotenv import load_dotenv
from core.config import load_config

load_dotenv()


def _get_token(key: str, config_path: str) -> str:
    """Get token from env var first, then config file."""
    env_val = os.environ.get(key, "")
    if env_val:
        return env_val
    config = load_config()
    return config.get("slack", {}).get(config_path, "")


SLACK_BOT_TOKEN = _get_token("SLACK_BOT_TOKEN", "bot_token")
SLACK_APP_TOKEN = _get_token("SLACK_APP_TOKEN", "app_token")


def validate():
    if not SLACK_BOT_TOKEN:
        raise RuntimeError(
            "Slack bot token not found. Run 'python setup.py' to configure, "
            "or set SLACK_BOT_TOKEN environment variable."
        )
    if not SLACK_APP_TOKEN:
        raise RuntimeError(
            "Slack app token not found. Run 'python setup.py' to configure, "
            "or set SLACK_APP_TOKEN environment variable."
        )
