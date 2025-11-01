import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    def _generate_key(self, prefix: str, **kwargs: Any) -> str:
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True, default=str)
        hash_suffix = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_suffix}"

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        expires_at = entry.get("expires_at")
        if not expires_at:
            return True
        return datetime.now(timezone.utc) > expires_at

    async def get(self, prefix: str, **kwargs: Any) -> Optional[Any]:
        async with self._lock:
            key = self._generate_key(prefix, **kwargs)
            entry = self._cache.get(key)

            if not entry:
                logger.debug(f"Cache não encontrado: {key}")
                return None

            if self._is_expired(entry):
                logger.debug(f"Cache expirado: {key}")
                del self._cache[key]
                return None

            logger.debug(f"Cache encontrado: {key}")
            return entry.get("value")

    async def set(self, prefix: str, value: Any, ttl_seconds: Optional[int] = None, **kwargs: Any) -> None:
        async with self._lock:
            key = self._generate_key(prefix, **kwargs)
            ttl = ttl_seconds or self.ttl_seconds
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

            self._cache[key] = {"value": value, "expires_at": expires_at}
            logger.debug(f"Cache definido: {key} (TTL: {ttl}s)")

    async def delete(self, prefix: str, **kwargs: Any) -> None:
        async with self._lock:
            key = self._generate_key(prefix, **kwargs)
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deletado: {key}")

    async def clear_prefix(self, prefix: str) -> None:
        async with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{prefix}:")]
            for key in keys_to_delete:
                del self._cache[key]
            logger.debug(f"Cache limpo para prefixo: {prefix} ({len(keys_to_delete)} chaves)")

    async def clear_all(self) -> None:
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache limpo: {count} chaves removidas")

    def get_stats(self) -> Dict[str, Any]:
        total_keys = len(self._cache)
        expired_keys = sum(1 for entry in self._cache.values() if self._is_expired(entry))

        return {
            "total_keys": total_keys,
            "expired_keys": expired_keys,
            "active_keys": total_keys - expired_keys,
        }

    def count_keys_by_prefix(self, prefix: str) -> int:
        return sum(1 for k in self._cache.keys() if k.startswith(f"{prefix}:"))

    def key_exists(self, prefix: str, **kwargs: Any) -> bool:
        key = self._generate_key(prefix, **kwargs)
        return key in self._cache
