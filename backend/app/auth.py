"""Shared-secret API-key auth. Enabled only when API_KEY is configured."""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from .config import get_settings


def _ok(expected: str, provided: str | None) -> bool:
    if not expected:
        return True  # auth disabled (no API_KEY set)
    return bool(provided) and secrets.compare_digest(provided, expected)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not _ok(get_settings().api_key, x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
