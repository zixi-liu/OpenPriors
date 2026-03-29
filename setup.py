"""
OpenPriors CLI Setup

Interactive terminal setup for API key configuration.
Usage: python setup.py
"""

import json
from core.config import load_config, save_config, ensure_dirs, CONFIG_FILE

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
    print("  Choose your LLM provider:")
    print()
    for key, (_, name, model) in PROVIDERS.items():
        print(f"    {key}. {name} ({model})")
    print()

    choice = input("  Provider [1]: ").strip() or "1"
    if choice not in PROVIDERS:
        print("  Invalid choice. Using Gemini.")
        choice = "1"

    provider_id, provider_name, default_model = PROVIDERS[choice]
    print()

    api_key = input(f"  {provider_name} API key: ").strip()
    if not api_key:
        print("  No API key provided. Exiting.")
        return

    config = load_config()
    config["llm"] = {
        "provider": provider_id,
        "api_key": api_key,
        "model": default_model,
    }
    save_config(config)

    print()
    print(f"  Done! Config saved to {CONFIG_FILE}")
    print(f"  Provider: {provider_name}")
    print(f"  Model: {default_model}")
    print()
    print("  Start the server:")
    print("    python app.py")
    print()


if __name__ == "__main__":
    setup()
