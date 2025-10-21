import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_duration: int = 60,
        half_open_attempts: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.half_open_attempts = half_open_attempts
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info("Circuit breaker: transicionando para HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    time_remaining = self._time_until_retry()
                    logger.warning(f"Circuit breaker OPEN - retry em {time_remaining}s")
                    raise Exception(f"Circuit breaker está aberto. Retry em {time_remaining}s")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True

        elapsed = datetime.now() - self.last_failure_time
        return elapsed.total_seconds() >= self.timeout_duration

    def _time_until_retry(self) -> int:
        if self.last_failure_time is None:
            return 0

        elapsed = datetime.now() - self.last_failure_time
        remaining = self.timeout_duration - elapsed.total_seconds()
        return max(0, int(remaining))

    async def _on_success(self):
        async with self._lock:
            self.failure_count = 0

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_attempts:
                    logger.info("Circuit breaker: transicionando para CLOSED")
                    self.state = CircuitState.CLOSED
                    self.success_count = 0

    async def _on_failure(self):
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker: falha durante HALF_OPEN, voltando para OPEN")
                self.state = CircuitState.OPEN
                self.success_count = 0
            elif self.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit breaker: threshold atingido ({self.failure_count}), abrindo")
                self.state = CircuitState.OPEN

    def get_state(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "time_until_retry": self._time_until_retry() if self.state == CircuitState.OPEN else 0,
        }
