from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.channels import ensure_default_channel


async def get_or_create_user(session: AsyncSession, clerk_user_id: str, email: str | None) -> User:
    result = await session.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        if email and user.email != email:
            user.email = email
        await ensure_default_channel(session, user)
        await session.commit()
        await session.refresh(user)
        return user

    user = User(clerk_user_id=clerk_user_id, email=email)
    session.add(user)
    await session.flush()
    await ensure_default_channel(session, user)
    await session.commit()
    await session.refresh(user)
    return user
