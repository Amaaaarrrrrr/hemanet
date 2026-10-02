"""Secure HTTP response headers (blueprint §R.2).

The API only returns JSON, so the CSP forbids everything. HSTS is sent only in
environments served over TLS (not local/ci).
"""

from flask import Flask, Response

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
HSTS_VALUE = "max-age=31536000; includeSubDomains"


def init_security_headers(app: Flask, *, hsts: bool) -> None:
    @app.after_request
    def _headers(response: Response) -> Response:
        headers = response.headers
        headers.setdefault("Content-Security-Policy", API_CSP)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        # API responses may contain personal data: never cache by default.
        headers.setdefault("Cache-Control", "no-store")
        if hsts:
            headers.setdefault("Strict-Transport-Security", HSTS_VALUE)
        return response
