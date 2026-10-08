import os
import json

SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "settings.json"
)

# ── Defaults ─────────────────────────────────────────────────
DEFAULTS = {
    "sender_name": "Alex",
    "company_name": "Autocloser",
    "calendly_link": "",
    "cycle_interval_minutes": 15,
    "pipeline_mode": "ai",
    "email_tone": "conversational",
    "auto_confirm_meetings": False,
    "auto_create_invoices": False,
    "default_service_id": "2",
    "max_email_words": 100,
    "notifications_enabled": True,
}

# In-memory cache (loaded once, refreshed on explicit load)
_cache: dict[str, object] | None = None


def load_settings() -> dict[str, object]:
    global _cache

    settings = dict(DEFAULTS)

    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                user_settings = json.load(f)
            settings.update(user_settings)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[SETTINGS] Warning: Could not read {SETTINGS_PATH}: {e}")
            print("[SETTINGS] Using defaults.")

    _cache = settings
    return settings


def save_settings(settings: dict[str, object]) -> None:
    global _cache

    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

    _cache = settings
    print(f"[SETTINGS] Saved to {SETTINGS_PATH}")


def get(key: str, default=None):
    global _cache

    if _cache is None:
        _cache = load_settings()

    return _cache.get(key, default if default is not None else DEFAULTS.get(key))


def update(key: str, value) -> bool:
    global _cache

    if _cache is None:
        _cache = load_settings()

    current_settings = _cache

    if key not in DEFAULTS:
        print(f"[SETTINGS] Unknown setting: '{key}'")
        print(f"[SETTINGS] Valid settings: {', '.join(sorted(DEFAULTS.keys()))}")
        return False

    # Type coercion based on the default's type
    expected_type = type(DEFAULTS[key])
    try:
        if expected_type == bool:
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes", "on")
            else:
                value = bool(value)
        elif expected_type == int:
            value = int(value)
        elif expected_type == str:
            value = str(value)
    except (ValueError, TypeError) as e:
        print(f"[SETTINGS] Invalid value for '{key}': {e}")
        return False

    old_value = current_settings.get(key)
    current_settings[key] = value
    save_settings(current_settings)

    print(f"[SETTINGS] Updated '{key}': {repr(old_value)} → {repr(value)}")
    return True


def reset() -> dict:
    save_settings(dict(DEFAULTS))
    print("[SETTINGS] All settings reset to defaults.")
    return dict(DEFAULTS)


def display() -> str:
    global _cache

    if _cache is None:
        _cache = load_settings()

    current_settings = _cache

    lines = []
    lines.append("═" * 55)
    lines.append("  ⚙️  AutoCloser Settings")
    lines.append("═" * 55)

    for key in sorted(current_settings.keys()):
        value = current_settings[key]
        default = DEFAULTS.get(key)
        marker = " " if value == default else "✏️"
        lines.append(f"  {marker} {key:30s} = {repr(value)}")

    lines.append("═" * 55)
    lines.append("  (✏️ = modified from default)")
    lines.append("")

    return "\n".join(lines)


