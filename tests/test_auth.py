"""Tests for auth service (pure logic, no DB)."""
import pytest
from app.services.auth import hash_key, hash_password, verify_password


class TestHashKey:
    def test_deterministic(self):
        assert hash_key("test-key") == hash_key("test-key")

    def test_different_keys_different_hash(self):
        assert hash_key("key-a") != hash_key("key-b")

    def test_non_empty(self):
        assert len(hash_key("any")) > 0


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "my-secure-password-123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_unique_salts(self):
        """Same password should produce different hashes due to random salt."""
        pwd = "same-password"
        assert hash_password(pwd) != hash_password(pwd)
