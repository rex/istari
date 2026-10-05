"""Async engine lifecycle. Created inside the FastAPI lifespan, never at import."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(url: str, *, pool_size: int = 5, max_overflow: int = 10) -> AsyncEngine:
    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=False,
    )


async def dispose_engine(engine: AsyncEngine) -> None:
    await engine.dispose()
