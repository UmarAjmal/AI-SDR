import time
import asyncio
import logging
import secrets
from typing import Optional
from packages.common.config import settings

logger = logging.getLogger("codenter.lock")

# In-memory lock registry for offline/testing environments
_MEMORY_LOCKS: dict[str, tuple[str, float]] = {}
_MEMORY_LOCK_MUTEX = asyncio.Lock()

class LockAcquisitionError(Exception):
    pass

class DistributedLock:
    """
    Distributed lock with TTL protecting against double-sends and race conditions.
    Connects to Redis with automatic fallback to in-memory locking for offline tests.
    """
    def __init__(self, key: str, ttl_seconds: int = 30, retry_delay: float = 0.1, max_retries: int = 3):
        self.key = f"codenter_lock:{key}"
        self.ttl_seconds = ttl_seconds
        self.token = secrets.token_hex(16)
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.redis_client = None
        self._is_memory_lock = False
        self._acquired = False

    @property
    def acquired(self) -> bool:
        return self._acquired

    async def _get_redis(self):
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.05,
                socket_timeout=0.05
            )
            await client.ping()
            return client
        except Exception:
            return None

    async def acquire(self) -> bool:
        redis_conn = await self._get_redis()
        if redis_conn:
            try:
                for _ in range(self.max_retries + 1):
                    acquired = await redis_conn.set(self.key, self.token, nx=True, ex=self.ttl_seconds)
                    if acquired:
                        self.redis_client = redis_conn
                        self._acquired = True
                        return True
                    await asyncio.sleep(self.retry_delay)
                await redis_conn.aclose()
                return False
            except Exception as e:
                logger.warning(f"Redis connection failed ({e}); falling back to in-memory lock.")
                try:
                    await redis_conn.aclose()
                except Exception:
                    pass

        # In-memory fallback
        self._is_memory_lock = True
        now = time.monotonic()
        for _ in range(self.max_retries + 1):
            async with _MEMORY_LOCK_MUTEX:
                existing = _MEMORY_LOCKS.get(self.key)
                if existing is None or existing[1] < now:
                    _MEMORY_LOCKS[self.key] = (self.token, now + self.ttl_seconds)
                    self._acquired = True
                    return True
            await asyncio.sleep(self.retry_delay)
            now = time.monotonic()

        return False

    async def release(self):
        self._acquired = False
        if self.redis_client:
            try:
                # Release only if token matches (standard Redis lock release script)
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                await self.redis_client.eval(lua_script, 1, self.key, self.token)
            except Exception as e:
                logger.warning(f"Failed to release Redis lock {self.key}: {e}")
            finally:
                try:
                    await self.redis_client.aclose()
                except Exception:
                    pass
        elif self._is_memory_lock:
            async with _MEMORY_LOCK_MUTEX:
                existing = _MEMORY_LOCKS.get(self.key)
                if existing and existing[0] == self.token:
                    del _MEMORY_LOCKS[self.key]

    async def __aenter__(self):
        acquired = await self.acquire()
        if not acquired:
            raise LockAcquisitionError(f"Could not acquire lock for key '{self.key}' within timeout")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
