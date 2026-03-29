"""
OpenPriors CLI Setup

Interactive terminal setup — LLM provider, Slack integration, and daemon.
Usage: python setup.py
"""

import json
import os
import sys
import random
import platform
from core.config import load_config, save_config, ensure_dirs, CONFIG_FILE

LEARNING_QUOTES = [
    "What we learn with pleasure we never forget. — Alfred Mercier",
    "Learning is not attained by chance, it must be sought for with ardor. — Abigail Adams",
    "The beautiful thing about learning is that nobody can take it away from you. — B.B. King",
]

PROVIDERS = {
    "1": ("gemini", "Google Gemini", "gemini/gemini-2.5-flash"),
    "2": ("openai", "OpenAI", "gpt-4o"),
    "3": ("anthropic", "Anthropic", "claude-sonnet-4-20250514"),
}


def setup():
    print()
    print("  OpenPriors — Turn what you learn into what you do.")
    print("  ─────────────────────────────────────────────────")
    print()

    config = load_config()

    # ── Step 1: LLM Provider ──
    print("  Step 1: LLM Provider")
    print()
    for key, (_, name, model) in PROVIDERS.items():
        print(f"    {key}. {name} ({model})")
    print()

    existing_provider = config.get("llm", {}).get("provider", "")
    if existing_provider:
        print(f"  Current: {existing_provider}")

    choice = input("  Provider [1]: ").strip() or "1"
    if choice not in PROVIDERS:
        print("  Invalid choice. Using Gemini.")
        choice = "1"

    provider_id, provider_name, default_model = PROVIDERS[choice]
    print()

    existing_key = config.get("llm", {}).get("api_key", "")
    if existing_key:
        masked = existing_key[:8] + "..." + existing_key[-4:]
        print(f"  Current key: {masked}")
        change_key = input("  Change key? [y/N]: ").strip().lower()
        if change_key != "y":
            api_key = existing_key
        else:
            api_key = input(f"  {provider_name} API key: ").strip()
    else:
        api_key = input(f"  {provider_name} API key: ").strip()

    if not api_key:
        print("  No API key provided. Exiting.")
        return

    config["llm"] = {
        "provider": provider_id,
        "api_key": api_key,
        "model": default_model,
    }

    print(f"  ✓ {provider_name} configured")
    print()

    # ── Step 2: Slack Integration (optional) ──
    print("  Step 2: Slack Integration (optional)")
    print()

    existing_slack = config.get("slack", {})
    if existing_slack.get("bot_token"):
        masked_bot = existing_slack["bot_token"][:10] + "..."
        print(f"  Current bot token: {masked_bot}")
        reconfigure = input("  Reconfigure Slack? [y/N]: ").strip().lower()
        if reconfigure != "y":
            print("  ✓ Slack kept as-is")
            print()
            _finalize(config)
            return

    connect_slack = input("  Connect to Slack? [y/N]: ").strip().lower()
    if connect_slack == "y":
        print()
        print("  To set up Slack, you need two tokens from api.slack.com/apps:")
        print()
        print("    1. Create a new Slack App (or use existing)")
        print("    2. Enable Socket Mode → copy App Token (xapp-...)")
        print("    3. Add Bot Scopes: channels:history, chat:write, reactions:write")
        print("    4. Subscribe to Events: message.channels, message.im")
        print("    5. Install to workspace → copy Bot Token (xoxb-...)")
        print()

        # Check env vars first
        env_bot = os.environ.get("SLACK_BOT_TOKEN", "")
        env_app = os.environ.get("SLACK_APP_TOKEN", "")
        if env_bot and env_app:
            use_env = input(f"  Found tokens in env vars. Use them? [Y/n]: ").strip().lower()
            if use_env != "n":
                config["slack"] = {
                    "bot_token": env_bot,
                    "app_token": env_app,
                }
                print("  ✓ Slack configured from environment")
                print()
                _finalize(config)
                return

        bot_token = input("  Bot Token (xoxb-...): ").strip()
        app_token = input("  App Token (xapp-...): ").strip()

        if bot_token and app_token:
            config["slack"] = {
                "bot_token": bot_token,
                "app_token": app_token,
            }
            print("  ✓ Slack configured")
        else:
            print("  Skipping Slack — you can set it up later.")
    else:
        print("  Skipping Slack.")

    print()
    _finalize(config)


def _finalize(config: dict):
    save_config(config)

    print(f"  Config saved to {CONFIG_FILE}")
    print()

    # ── Step 3: Start services ──
    print("  Step 3: Start")
    print()
    print("    Start the web app:")
    print("      python app.py")
    print()

    if config.get("slack", {}).get("bot_token"):
        print("    Start the Slack bot:")
        print("      python -m slack_bot.bot")
        print()

        install_daemon = input("  Auto-start Slack bot on login? [y/N]: ").strip().lower()
        if install_daemon == "y":
            _install_daemon()
    print()
    print(f"  \"{random.choice(LEARNING_QUOTES)}\"")
    print()


def _install_daemon():
    """Install a launchd (macOS) or systemd (Linux) service for the Slack bot."""
    system = platform.system()

    if system == "Darwin":
        _install_launchd()
    elif system == "Linux":
        _install_systemd()
    else:
        print(f"  Auto-start not supported on {system}. Run manually.")


def _install_launchd():
    """Install macOS launchd agent for the Slack bot."""
    import subprocess

    label = "com.openpriors.slack-bot"
    plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
    python_path = sys.executable
    project_dir = os.path.dirname(os.path.abspath(__file__))

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>slack_bot.bot</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{project_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{os.path.expanduser("~/.openpriors/slack-bot.log")}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.expanduser("~/.openpriors/slack-bot.log")}</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>"""

    os.makedirs(os.path.dirname(plist_path), exist_ok=True)

    # Unload existing if present
    if os.path.exists(plist_path):
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)

    with open(plist_path, "w") as f:
        f.write(plist_content)

    result = subprocess.run(["launchctl", "load", plist_path], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ Slack bot installed as launchd service")
        print(f"    Logs: ~/.openpriors/slack-bot.log")
        print(f"    Stop: launchctl unload {plist_path}")
    else:
        print(f"  Failed to install: {result.stderr}")


def _install_systemd():
    """Install Linux systemd user service for the Slack bot."""
    import subprocess

    service_name = "openpriors-slack-bot"
    service_dir = os.path.expanduser("~/.config/systemd/user")
    service_path = os.path.join(service_dir, f"{service_name}.service")
    python_path = sys.executable
    project_dir = os.path.dirname(os.path.abspath(__file__))

    service_content = f"""[Unit]
Description=OpenPriors Slack Bot
After=network.target

[Service]
ExecStart={python_path} -m slack_bot.bot
WorkingDirectory={project_dir}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""

    os.makedirs(service_dir, exist_ok=True)
    with open(service_path, "w") as f:
        f.write(service_content)

    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    result = subprocess.run(
        ["systemctl", "--user", "enable", "--now", service_name],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  ✓ Slack bot installed as systemd service")
        print(f"    Logs: journalctl --user -u {service_name}")
        print(f"    Stop: systemctl --user stop {service_name}")
    else:
        print(f"  Failed to install: {result.stderr}")


if __name__ == "__main__":
    setup()
