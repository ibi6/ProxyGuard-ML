"""HTTP middleware: access log + basic security headers."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("proxyguard.access")


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, duration (skip static assets)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        path = request.url.path
        if not path.startswith("/static"):
            ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s -> %s (%.1fms)",
                request.method,
                path,
                response.status_code,
                ms,
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach conservative security headers for a local/demo web app.

    Note: This is not a full multi-tenant hardening suite. CSP is intentionally
    permissive enough for Tailwind CDN + Chart.js used by the console.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        # Allow CDN scripts used by templates; tighten if you self-host assets.
        response.headers.setdefault(
            "Content-Security-Policy",
            "; ".join(
                [
                    "default-src 'self'",
                    "img-src 'self' data: blob:",
                    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com",
                    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net",
                    "connect-src 'self'",
                    "font-src 'self' data:",
                    "frame-ancestors 'none'",
                    "base-uri 'self'",
                    "form-action 'self'",
                ]
            ),
        )
        return response
