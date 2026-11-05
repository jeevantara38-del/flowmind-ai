"""FlowMind AI - Retry Engine."""

from dataclasses import dataclass, field
import random
import time
from typing import Any, Callable, Optional, Sequence, Tuple, Type

from flowmind.errors import NonIdempotentRetryError


@dataclass
class RetryPolicy:
    max_retries: int = 3
    initial_delay: float = 0.1
    max_delay: float = 10.0
    backoff_factor: float = 1.5
    jitter: bool = True
    jitter_type: str = "full"
    retryable_exceptions: Sequence[Type[BaseException]] = field(
        default_factory=lambda: (Exception,)
    )
    non_retryable_exceptions: Sequence[Type[BaseException]] = field(
        default_factory=lambda: (
            KeyboardInterrupt,
            SystemExit,
            MemoryError,
            NonIdempotentRetryError,
        )
    )

    def calculate_delay(self, attempt: int) -> float:
        if attempt < 0:
            attempt = 0
        raw_backoff = self.initial_delay * (self.backoff_factor ** attempt)
        capped_backoff = min(self.max_delay, raw_backoff)

        if not self.jitter or self.jitter_type == "none":
            return capped_backoff
        if self.jitter_type == "equal":
            half = capped_backoff / 2.0
            return half + random.uniform(0, half)
        return random.uniform(0, capped_backoff)

    def is_retryable(self, exception: BaseException) -> bool:
        for exc_type in self.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        for exc_type in self.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        return False

    def check_retry(
        self,
        attempt: int,
        exception: BaseException,
        is_idempotent: bool,
    ) -> Tuple[bool, Optional[str]]:
        if not is_idempotent:
            return (
                False,
                f"Task is non-idempotent (is_idempotent=False). Blind retries are blocked "
                f"to prevent duplicate external side-effects.",
            )
        if attempt >= self.max_retries:
            return (
                False,
                f"Max retry limit ({self.max_retries}) reached. Attempt count: {attempt + 1}.",
            )
        if not self.is_retryable(exception):
            return (
                False,
                f"Exception '{type(exception).__name__}' is configured as non-retryable.",
            )
        return True, "Retry criteria satisfied."


NO_RETRY = RetryPolicy(max_retries=0)
STANDARD_RETRY = RetryPolicy(max_retries=3, initial_delay=0.05, backoff_factor=1.5)
AGGRESSIVE_RETRY = RetryPolicy(max_retries=5, initial_delay=0.02, backoff_factor=1.2)
