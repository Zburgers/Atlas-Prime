from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.auth import (
    AuthConfigurationError,
    InvalidAuthTokenError,
    dev_auth_headers_enabled,
    verify_clerk_session_token,
)
from app.services.processing_queue import ProcessingQueue
from app.services.storage import MinioOriginalStorage, MinioProcessedHlsStorage, OriginalStorage, ProcessedHlsStorage
from app.services.users import get_or_create_user


@dataclass(frozen=True)
class CurrentIdentity:
    clerk_user_id: str
    email: str | None = None


async def current_identity(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    clerk_user_id: Annotated[str | None, Header(alias="X-Atlas-Dev-Clerk-User-Id")] = None,
    email: Annotated[str | None, Header(alias="X-Atlas-Dev-Email")] = None,
) -> CurrentIdentity:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token is None:
        token = request.cookies.get("__session")

    if token:
        try:
            claims = await verify_clerk_session_token(token)
        except AuthConfigurationError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "AuthConfigurationError", "message": "Clerk authentication is not configured"},
            ) from None
        except InvalidAuthTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Unauthorized", "message": "Invalid or expired Clerk session"},
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        return CurrentIdentity(clerk_user_id=claims.clerk_user_id, email=claims.email)

    if dev_auth_headers_enabled() and clerk_user_id:
        return CurrentIdentity(clerk_user_id=clerk_user_id, email=email)

    if clerk_user_id and not dev_auth_headers_enabled():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "Development auth headers are disabled"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "Unauthorized", "message": "Missing Clerk identity"},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_identity(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    clerk_user_id: Annotated[str | None, Header(alias="X-Atlas-Dev-Clerk-User-Id")] = None,
    email: Annotated[str | None, Header(alias="X-Atlas-Dev-Email")] = None,
) -> CurrentIdentity | None:
    try:
        return await current_identity(request, authorization, clerk_user_id, email)
    except HTTPException as exc:
        if (
            exc.status_code == status.HTTP_401_UNAUTHORIZED
            and not authorization
            and not request.cookies.get("__session")
            and not clerk_user_id
        ):
            return None
        raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]
IdentityDep = Annotated[CurrentIdentity, Depends(current_identity)]
OptionalIdentityDep = Annotated[CurrentIdentity | None, Depends(optional_identity)]


async def current_user(session: SessionDep, identity: IdentityDep):
    return await get_or_create_user(session, identity.clerk_user_id, identity.email)


async def optional_current_user(session: SessionDep, identity: OptionalIdentityDep):
    if identity is None:
        return None
    return await get_or_create_user(session, identity.clerk_user_id, identity.email)


CurrentUserDep = Annotated[object, Depends(current_user)]
OptionalCurrentUserDep = Annotated[object | None, Depends(optional_current_user)]


def get_original_storage() -> OriginalStorage:
    return MinioOriginalStorage()


def get_processed_hls_storage() -> ProcessedHlsStorage:
    return MinioProcessedHlsStorage()


def get_processing_queue() -> ProcessingQueue:
    return ProcessingQueue()


OriginalStorageDep = Annotated[OriginalStorage, Depends(get_original_storage)]
ProcessedHlsStorageDep = Annotated[ProcessedHlsStorage, Depends(get_processed_hls_storage)]
ProcessingQueueDep = Annotated[ProcessingQueue, Depends(get_processing_queue)]
