"""Shared settings schema and validation for PRDforge."""

DEFAULT_PROJECT_SETTINGS = {"claude_comment_replies": True}

# Whitelist: key -> (type, default)
SETTINGS_SCHEMA = {
    "claude_comment_replies": (bool, True),
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
        clean[key] = value
    return clean, errors
