"""Normalize responses returned by google_ml.predict_row / Ollama."""

import json
from typing import Any, Optional


def extract_ai_insight(value: Any) -> Optional[str]:
    """Return meaningful response text, or None for empty/malformed payloads.

    AlloyDB integrations can return a decoded object or a JSON string. Plain
    text is also accepted. An absent/blank ``response`` is reported to the
    caller as None so the UI can show an explicit unavailable state instead
    of silently treating it as a successful prediction.
    """
    if value is None:
        return None

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None

    parsed = value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Ollama adapters may return a plain-text response instead of JSON.
            return raw

    if isinstance(parsed, dict):
        response = parsed.get("response")
        if response is None:
            return None
        text = response if isinstance(response, str) else str(response)
        return text.strip() or None

    if isinstance(parsed, str):
        return parsed.strip() or None

    return None
