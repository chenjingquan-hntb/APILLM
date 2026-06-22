"""Tests for JWT token utilities (pure logic, no DB)."""
import time
import pytest
from app.services.jwt import (
    create_access_token,
    verify_access_token,
    create_refresh_token,
    hash_refresh_token,
    _b64_encode,
    _b64_decode,
)
from app.core.exceptions import AuthError


class TestBase64:
    def test_roundtrip(self):
        data = b"hello world"
        encoded = _b64_encode(data)
        decoded = _b64_decode(encoded)
        assert decoded == data

    def test_padding_handling(self):
        """URL-safe base64 without padding should decode correctly."""
        encoded = _b64_encode(b"test")
        assert "=" not in encoded
        decoded = _b64_decode(encoded)
        assert decoded == b"test"

    def test_empty(self):
        assert _b64_decode(_b64_encode(b"")) == b""


class TestAccessToken:
    def test_create_and_verify(self):
        token = create_access_token(user_id=42, role="admin")
        payload = verify_access_token(token)
        assert payload["sub"] == 42
        assert payload["role"] == "admin"
        assert "iat" in payload
        assert "exp" in payload

    def test_expired_token(self):
        # Manually create an expired token
        payload = (
            '{"alg":"HS256","typ":"JWT"}'
            + "."
            + _b64_encode(f'{{"sub":1,"role":"user","iat":0,"exp":1}}'.encode())
        )
        import hashlib, hmac
        from app.core.config import settings
        sig = _b64_encode(
            hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
        )
        expired = f"{payload}.{sig}"

        with pytest.raises(AuthError, match="expired"):
            verify_access_token(expired)

    def test_invalid_signature(self):
        token = create_access_token(user_id=1, role="user")
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(AuthError, match="signature"):
            verify_access_token(tampered)

    def test_invalid_format(self):
        with pytest.raises(AuthError, match="token format"):
            verify_access_token("not-a-valid-token")

        with pytest.raises(AuthError, match="token format"):
            verify_access_token("too.many.dots.here")

    def test_user_role_preserved(self):
        for role in ("admin", "user"):
            token = create_access_token(user_id=1, role=role)
            payload = verify_access_token(token)
            assert payload["role"] == role


class TestRefreshToken:
    def test_create_is_urlsafe(self):
        token = create_refresh_token()
        assert len(token) > 32
        # Should be URL-safe (no + or /)
        assert "+" not in token
        assert "/" not in token

    def test_hash_is_deterministic(self):
        raw = "test-refresh-token-value"
        assert hash_refresh_token(raw) == hash_refresh_token(raw)

    def test_hash_different_for_different_tokens(self):
        assert hash_refresh_token("token-a") != hash_refresh_token("token-b")

    def test_unique_tokens(self):
        tokens = {create_refresh_token() for _ in range(100)}
        assert len(tokens) == 100
