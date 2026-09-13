"""Unit tests for multi-tier query and embedding cache manager."""
import unittest
import time
from src.cache.cache_manager import CacheManager

class TestCache(unittest.TestCase):
    def setUp(self):
        self.cache = CacheManager()
        self.cache.clear()

    def test_query_cache_miss_then_hit(self):
        query = "What are the working hours?"
        payload = {"response": "Standard working hours are 9am to 5pm.", "citations": []}

        # First lookup: cache miss
        miss_res = self.cache.get_query(query)
        self.assertIsNone(miss_res)

        # Store in cache
        self.cache.set_query(query, payload, ttl_seconds=60)

        # Second lookup: cache hit
        hit_res = self.cache.get_query(query)
        self.assertIsNotNone(hit_res)
        self.assertEqual(hit_res["response"], payload["response"])

    def test_query_cache_ttl_expiration(self):
        query = "Temporary query"
        payload = {"response": "Temporary answer"}

        # Store with 0-second TTL (immediately expires)
        self.cache.set_query(query, payload, ttl_seconds=-1)

        expired_res = self.cache.get_query(query)
        self.assertIsNone(expired_res)

    def test_embedding_cache(self):
        text = "Semantic embedding input text."
        vector = [0.123, -0.456, 0.789]

        self.assertIsNone(self.cache.get_embedding(text))
        self.cache.set_embedding(text, vector, ttl_seconds=60)

        cached_vector = self.cache.get_embedding(text)
        self.assertEqual(cached_vector, vector)

    def test_cache_stats(self):
        self.cache.get_query("query_1")  # miss
        self.cache.set_query("query_1", {"response": "ok"})
        self.cache.get_query("query_1")  # hit

        stats = self.cache.get_stats()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["hit_rate"], 0.5)

if __name__ == "__main__":
    unittest.main()
