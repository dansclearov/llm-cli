"""User configuration management."""

import json
from pathlib import Path
from typing import Dict, Any

from platformdirs import user_config_dir


def get_user_config_path() -> Path:
    """Get the path to the user configuration file."""
    config_dir = Path(user_config_dir("llm_cli", ensure_exists=True))
    return config_dir / "config.json"


def load_user_config() -> Dict[str, Any]:
    """Load user configuration from file."""
    config_path = get_user_config_path()

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_user_config(config_data: Dict[str, Any]) -> None:
    """Save user configuration to file."""
    config_path = get_user_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
    except OSError:
        # Silently fail if we can't write the config file
        pass


def update_user_config(key: str, value: Any) -> None:
    """Update a specific key in the user configuration."""
    config = load_user_config()
    config[key] = value
    save_user_config(config)
