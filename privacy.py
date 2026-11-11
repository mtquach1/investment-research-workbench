"""Application privacy policy; deployment settings are never user-controlled."""

from fastapi import HTTPException

from config import Settings


def require_saved_runs(settings: Settings) -> None:
    if not settings.saved_runs_enabled:
        raise HTTPException(status_code=404, detail="Saved scenarios are disabled in session-only mode.")


def require_ai(settings: Settings) -> None:
    if not settings.ai_enabled:
        raise HTTPException(status_code=404, detail="AI processing is disabled.")


def clear_financial_session(state) -> None:
    """Drop application references, including legacy history and selected uploads.

    This is not secure erasure of memory, browser downloads, or external storage.
    """
    for key in list(state):
        del state[key]
