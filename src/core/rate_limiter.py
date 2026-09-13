"""Sliding-window rate limiter to protect endpoints against abuse and DoS."""
from __future__ import annotations

import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple

from src.core.logging import get_logger

logger = get_logger("rate_limiter")

class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self, default_limit: int = 30, window_seconds: int = 60) -> None:
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check_rate_limit(
        self,
        identifier: str,
        limit: int | None = None
    ) -> Tuple[bool, int, int]:
        """Checks if request is within rate limit.
        
        Returns:
            Tuple of (is_allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        now = time.time()
        max_allowed = limit or self.default_limit
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[identifier]
            # Prune timestamps outside the current sliding window
            self._requests[identifier] = [t for t in timestamps if t > cutoff]
            current_count = len(self._requests[identifier])

            if current_count >= max_allowed:
                oldest = self._requests[identifier][0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                logger.warning(f"Rate limit exceeded for '{identifier}' ({current_count}/{max_allowed})")
                return False, 0, retry_after

            # Record this request timestamp
            self._requests[identifier].append(now)
            remaining = max(0, max_allowed - (current_count + 1))
            return True, remaining, 0

    def reset(self, identifier: str | None = None) -> None:
        """Resets rate limit records for an identifier or all callers."""
        with self._lock:
            if identifier:
                self._requests.pop(identifier, None)
            else:
                self._requests.clear()

# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter(default_limit=30, window_seconds=60)
