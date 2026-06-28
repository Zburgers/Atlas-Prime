from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient


class AuthConfigurationError(RuntimeError):
    pass


class InvalidAuthTokenError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClerkSessionClaims:
    clerk_user_id: str
    email: str | None = None
    session_id: str | None = None


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def dev_auth_headers_enabled() -> bool:
    return _env("ATLAS_ALLOW_DEV_AUTH_HEADERS").lower() in {"1", "true", "yes"}


def _publishable_key() -> str:
    return _env("CLERK_PUBLISHABLE_KEY") or _env("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")


def _frontend_api_url_from_publishable_key() -> str | None:
    key = _publishable_key()
    if not key:
        return None
    try:
        encoded = key.split("_", 2)[2].rstrip("$")
        padding = "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(f"{encoded}{padding}").decode("utf-8").rstrip("$")
    except (IndexError, UnicodeDecodeError, ValueError):
        return None
    if not decoded:
        return None
    return decoded if decoded.startswith("https://") else f"https://{decoded}"


def clerk_issuer() -> str:
    configured = _env("CLERK_ISSUER").rstrip("/")
    if configured:
        return configured
    frontend_api_url = _frontend_api_url_from_publishable_key()
    if frontend_api_url:
        return frontend_api_url.rstrip("/")
    raise AuthConfigurationError("Clerk issuer is not configured")


def clerk_jwks_url() -> str:
    configured = _env("CLERK_JWKS_URL").rstrip("/")
    if configured:
        return configured
    return f"{clerk_issuer()}/.well-known/jwks.json"


def authorized_parties() -> list[str]:
    raw = _env("CLERK_AUTHORIZED_PARTIES")
    return [value.strip().rstrip("/") for value in raw.split(",") if value.strip()]


@lru_cache(maxsize=4)
def _jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def _email_from_claims(claims: dict[str, Any]) -> str | None:
    for key in ("email", "primary_email_address", "primary_email_address_email_address"):
        value = claims.get(key)
        if isinstance(value, str) and value:
            return value
    return None


async def verify_clerk_session_token(token: str) -> ClerkSessionClaims:
    try:
        signing_key = _jwk_client(clerk_jwks_url()).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=clerk_issuer(),
            options={"require": ["exp", "iat", "nbf", "sub"]},
        )
    except AuthConfigurationError:
        raise
    except Exception as exc:
        raise InvalidAuthTokenError("Invalid Clerk session token") from exc

    parties = authorized_parties()
    token_party = claims.get("azp")
    if parties and token_party and str(token_party).rstrip("/") not in parties:
        raise InvalidAuthTokenError("Invalid Clerk token authorized party")

    session_status = claims.get("sts")
    if session_status == "pending":
        raise InvalidAuthTokenError("Clerk session is pending")

    clerk_user_id = claims.get("sub")
    if not isinstance(clerk_user_id, str) or not clerk_user_id:
        raise InvalidAuthTokenError("Clerk token subject is missing")

    session_id = claims.get("sid")
    return ClerkSessionClaims(
        clerk_user_id=clerk_user_id,
        email=_email_from_claims(claims),
        session_id=session_id if isinstance(session_id, str) else None,
    )
