import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional

from src.app.config import settings

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_attempts: Optional[int] = None,
    delay_seconds: Optional[float] = None,
    exponential_backoff: bool = True,
    exceptions: tuple = (Exception,),
):
    max_attempts = max_attempts or settings.MAX_RETRY_ATTEMPTS
    delay_seconds = delay_seconds or settings.RETRY_DELAY_SECONDS

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = delay_seconds
                        if exponential_backoff:
                            delay = delay_seconds * (2**attempt)

                        logger.warning(
                            f"Tentativa {attempt + 1}/{max_attempts} falhou para {func.__name__}: {e}. "
                            f"Tentando novamente em {delay}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Todas as {max_attempts} tentativas falharam para {func.__name__}. " f"Último erro: {e}"
                        )

            raise last_exception

        return async_wrapper

    return decorator


class RetryableError(Exception):
    pass


class NonRetryableError(Exception):
    pass