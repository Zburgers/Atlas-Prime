import asyncio
import time

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

from app.services import auth as auth_service


def _private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_verify_clerk_session_token_validates_issuer_and_authorized_party(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = _private_key()
    issuer = "https://example.clerk.accounts.dev"
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user_clerk_123",
            "sid": "sess_123",
            "iss": issuer,
            "azp": "http://localhost:3001",
            "iat": now,
            "nbf": now - 5,
            "exp": now + 300,
            "email": "owner@example.com",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    class StubSigningKey:
        key = private_key.public_key()

    class StubJwkClient:
        def get_signing_key_from_jwt(self, received_token: str) -> StubSigningKey:
            assert received_token == token
            return StubSigningKey()

    monkeypatch.setenv("CLERK_ISSUER", issuer)
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:3001")
    monkeypatch.setattr(auth_service, "_jwk_client", lambda _url: StubJwkClient())

    claims = asyncio.run(auth_service.verify_clerk_session_token(token))

    assert claims.clerk_user_id == "user_clerk_123"
    assert claims.email == "owner@example.com"
    assert claims.session_id == "sess_123"


def test_verify_clerk_session_token_rejects_wrong_authorized_party(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = _private_key()
    issuer = "https://example.clerk.accounts.dev"
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user_clerk_123",
            "iss": issuer,
            "azp": "https://wrong.example",
            "iat": now,
            "nbf": now - 5,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    class StubSigningKey:
        key = private_key.public_key()

    class StubJwkClient:
        def get_signing_key_from_jwt(self, _token: str) -> StubSigningKey:
            return StubSigningKey()

    monkeypatch.setenv("CLERK_ISSUER", issuer)
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:3001")
    monkeypatch.setattr(auth_service, "_jwk_client", lambda _url: StubJwkClient())

    with pytest.raises(auth_service.InvalidAuthTokenError):
        asyncio.run(auth_service.verify_clerk_session_token(token))
