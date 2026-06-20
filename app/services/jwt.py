"""JWT token utilities for user authentication.

Uses HMAC-SHA256 with settings.secret_key.
- Access token: 15 min expiry, used for API authorization.
- Refresh token: 7 day expiry, stored as SHA-256 hash in DB, used to rotate access tokens.
"""
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

from app.core.config import settings
from app.core.exceptions import AuthError


ACCESS_TOKEN_EXPIRY = 900       # 15 minutes
REFRESH_TOKEN_EXPIRY = 604800   # 7 days
TOKEN_SEP = "."


def _b64_encode(data: bytes) -> str:
    """URL-safe base64 without padding."""
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(s: str) -> bytes:
    """URL-safe base64 decode (restores padding)."""
    import base64
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_access_token(user_id: int, role: str) -> str:
    """Create a signed JWT access token.

    Format: base64(header).base64(payload).hmac_signature
    """
    now = int(time.time())
    header = _b64_encode(b'{"alg":"HS256","typ":"JWT"}')
    payload_data = f'{{"sub":{user_id},"role":"{role}","iat":{now},"exp":{now + ACCESS_TOKEN_EXPIRY}}}'
    payload = _b64_encode(payload_data.encode())
    signing_input = f"{header}.{payload}"
    signature = _b64_encode(
        hmac.new(settings.secret_key.encode(), signing_input.encode(), hashlib.sha256).digest()
    )
    return f"{signing_input}.{signature}"


def verify_access_token(token: str) -> dict:
    """Verify and decode an access token. Raises AuthError on failure."""
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("Invalid token format")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}"

    # Verify signature
    expected_sig = _b64_encode(
        hmac.new(settings.secret_key.encode(), signing_input.encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(sig_b64.encode(), expected_sig.encode()):
        raise AuthError("Invalid token signature")

    # Decode payload
    try:
        import json
        payload = json.loads(_b64_decode(payload_b64))
    except Exception:
        raise AuthError("Invalid token payload")

    # Check expiry
    if payload.get("exp", 0) < time.time():
        raise AuthError("Token expired")

    return payload


def create_refresh_token() -> str:
    """Generate a cryptographically random refresh token (raw, unhashed)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw: str) -> str:
    """SHA-256 hash the refresh token for storage."""
    return hashlib.sha256(raw.encode()).hexdigest()
