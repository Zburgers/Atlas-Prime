from __future__ import annotations

import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def database_url() -> str:
    raw = env("DATABASE_URL", "postgresql+asyncpg://atlas:atlas@postgres:5432/atlas_prime")
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw
