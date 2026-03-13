"""Shared settings schema and validation for PRDforge."""

DEFAULT_PROJECT_SETTINGS = {
    "claude_comment_replies": True,
    "chat_enabled": False,
    "chat_provider": "claude_cli",
}
CHAT_PROVIDER_VALUES = {"claude_cli", "anthropic_api"}

# Whitelist: key -> (type, default)
SETTINGS_SCHEMA = {
    "claude_comment_replies": (bool, True),
    "chat_enabled": (bool, False),
    "chat_provider": (str, "claude_cli"),
}


def validate_settings(incoming: dict) -> tuple[dict, list[str]]:
    """Validate and filter settings. Returns (clean_dict, errors)."""
    clean = {}
    errors = []
    for key, value in incoming.items():
        if key not in SETTINGS_SCHEMA:
            errors.append(f"unknown setting '{key}'")
            continue
        expected_type, _ = SETTINGS_SCHEMA[key]
        if not isinstance(value, expected_type):
            errors.append(f"'{key}' must be {expected_type.__name__}")
            continue
        if key == "chat_provider" and value not in CHAT_PROVIDER_VALUES:
            allowed = ", ".join(sorted(CHAT_PROVIDER_VALUES))
            errors.append(f"'chat_provider' must be one of: {allowed}")
            continue
        clean[key] = value
    return clean, errors
