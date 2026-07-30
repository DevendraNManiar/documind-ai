"""Unit tests that run without a database or external services."""
from app.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_access_token("user-123")
    assert decode_token(token) == "user-123"


def test_jwt_rejects_garbage():
    assert decode_token("not-a-real-token") is None
