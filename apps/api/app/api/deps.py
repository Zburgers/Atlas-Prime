from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.users import get_or_create_user


@dataclass(frozen=True)
class CurrentIdentity:
    clerk_user_id: str
    email: str | None = None


async def current_identity(
    clerk_user_id: Annotated[str | None, Header(alias="X-Atlas-Dev-Clerk-User-Id")] = None,
    email: Annotated[str | None, Header(alias="X-Atlas-Dev-Email")] = None,
) -> CurrentIdentity:
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "Missing Clerk identity"},
        )
    return CurrentIdentity(clerk_user_id=clerk_user_id, email=email)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
IdentityDep = Annotated[CurrentIdentity, Depends(current_identity)]


async def current_user(session: SessionDep, identity: IdentityDep):
    return await get_or_create_user(session, identity.clerk_user_id, identity.email)


CurrentUserDep = Annotated[object, Depends(current_user)]
