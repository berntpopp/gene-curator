"""
Rate limiter for logging to prevent DOS from log loops.

Fixes Issue #20: Provides DOS protection against runaway log loops.
"""

from collections import deque
from time import time


class RateLimiter:
    """
    Simple rate limiter for logging operations.

    Prevents log flooding from runaway loops or errors.
    """

    def __init__(self, max_logs_per_second: int = 100):
        """
        Initialize rate limiter.

        Args:
            max_logs_per_second: Maximum logs allowed per second
        """
        self.max_logs = max_logs_per_second
        self.log_times: deque[float] = deque(maxlen=max_logs_per_second)
        self.dropped_count = 0

    def should_log(self) -> bool:
        """
        Check if logging should proceed based on rate limit.

        Returns:
            True if logging is allowed, False if rate limit exceeded
        """
        now = time()

        # Remove entries older than 1 second
        while self.log_times and now - self.log_times[0] > 1.0:
            self.log_times.popleft()

        # Check if we've hit the rate limit
        if len(self.log_times) >= self.max_logs:
            self.dropped_count += 1
            return False

        self.log_times.append(now)
        return True

    def get_dropped_count(self) -> int:
        """Get number of dropped logs."""
        return self.dropped_count

    def reset_dropped_count(self) -> int:
        """Reset and return dropped count."""
        count = self.dropped_count
        self.dropped_count = 0
        return count
