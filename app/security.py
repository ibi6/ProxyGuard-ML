"""Optional API token gate for mutating endpoints."""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import API_TOKEN


def auth_required() -> bool:
    """True when PROXYGUARD_TOKEN is configured."""
    return bool(API_TOKEN)


async def require_api_token(x_api_token: str | None = Header(default=None, alias="X-API-Token")):
    """If token is configured, require matching X-API-Token header on write APIs.

    Local demos leave PROXYGUARD_TOKEN empty and skip this check.
    """
    if not API_TOKEN:
        return
    if not x_api_token or x_api_token != API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="unauthorized: missing or invalid X-API-Token",
        )
