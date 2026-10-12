import asyncio
from typing import Protocol

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class DependencyProbe(Protocol):
    async def check(self) -> dict[str, bool]: ...


class InfrastructureProbe:
    def __init__(self, engine: AsyncEngine, redis: Redis) -> None:
        self.engine = engine
        self.redis = redis

    async def _database(self) -> bool:
        try:
            async with asyncio.timeout(3):
                async with self.engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
            return True
        except Exception:
            # Failure is explicitly returned; credentials and SQL stay out of public output.
            return False

    async def _redis(self) -> bool:
        try:
            async with asyncio.timeout(3):
                return bool(await self.redis.ping())
        except Exception:
            return False

    async def check(self) -> dict[str, bool]:
        database, redis = await asyncio.gather(self._database(), self._redis())
        return {"database": database, "redis": redis}
