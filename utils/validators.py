import re

def validate_tag_name(name: str) -> bool:
    """Validate tag name: alphanumeric + underscore, max 32 chars."""
    if not name or len(name) > 32:
        return False
    # Only alphanumeric and underscores
    return bool(re.match(r'^[a-zA-Z0-9_]+$', name))

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password: min 8 characters."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, ""
