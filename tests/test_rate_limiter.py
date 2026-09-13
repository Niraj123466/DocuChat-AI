"""Unit tests for sliding-window rate limiter."""
import unittest
from src.core.rate_limiter import SlidingWindowRateLimiter

class TestRateLimiter(unittest.TestCase):
    def test_rate_limiter_allows_under_limit(self):
        limiter = SlidingWindowRateLimiter(default_limit=5, window_seconds=10)
        for i in range(5):
            allowed, remaining, retry_after = limiter.check_rate_limit("client_1")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
            self.assertEqual(retry_after, 0)

    def test_rate_limiter_blocks_over_limit(self):
        limiter = SlidingWindowRateLimiter(default_limit=3, window_seconds=10)
        # Use up allowed quota
        for _ in range(3):
            allowed, _, _ = limiter.check_rate_limit("client_blocked")
            self.assertTrue(allowed)

        # 4th request must be rejected
        allowed, remaining, retry_after = limiter.check_rate_limit("client_blocked")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)

    def test_rate_limiter_per_client_isolation(self):
        limiter = SlidingWindowRateLimiter(default_limit=2, window_seconds=10)
        # Exhaust client A
        limiter.check_rate_limit("client_a")
        limiter.check_rate_limit("client_a")
        self.assertFalse(limiter.check_rate_limit("client_a")[0])

        # Client B should still be allowed
        self.assertTrue(limiter.check_rate_limit("client_b")[0])

if __name__ == "__main__":
    unittest.main()
