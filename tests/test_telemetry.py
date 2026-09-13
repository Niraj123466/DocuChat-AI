"""Unit tests for Prometheus metrics export and OpenTelemetry tracing."""
import unittest
from fastapi.testclient import TestClient
from src.core.telemetry import PrometheusMetrics, trace_span
from src.api.app import app

class TestTelemetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        from src.core.security import JWTHandler
        cls.token = JWTHandler.create_access_token(subject="admin@docuchat.ai", role="admin")
        cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}

    def test_prometheus_counter_and_histogram(self):
        m = PrometheusMetrics()
        m.inc_counter("test_counter", 5.0, labels={"env": "test"})
        m.observe_histogram("test_latency", 0.15, labels={"route": "chat"})

        scrape_text = m.generate_scrape_text()
        self.assertIn("# TYPE test_counter counter", scrape_text)
        self.assertIn('test_counter{env="test"} 5.0', scrape_text)
        self.assertIn("# TYPE test_latency histogram", scrape_text)
        self.assertIn("test_latency_bucket", scrape_text)
        self.assertIn("test_latency_count", scrape_text)

    def test_trace_span_context_manager(self):
        executed = False
        with trace_span("test_workflow_step", attributes={"step": 1}):
            executed = True
        self.assertTrue(executed)

    def test_metrics_http_endpoint(self):
        # Trigger an HTTP request to generate telemetry
        self.client.get("/api/v1/health")

        # Scrape /metrics
        resp = self.client.get("/metrics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp.headers["content-type"])
        self.assertIn("docuchat_requests_total", resp.text)
        self.assertIn("docuchat_request_latency_seconds", resp.text)

    def test_chat_cache_hit_metadata(self):
        payload = {"message": "Repeatable test query for cache hit validation"}

        # 1st call: Cache miss
        resp1 = self.client.post("/api/v1/chat", json=payload, headers=self.auth_headers)
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertFalse(data1["metadata"]["cache_hit"])

        # 2nd call: Cache hit
        resp2 = self.client.post("/api/v1/chat", json=payload, headers=self.auth_headers)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2["metadata"]["cache_hit"])
        self.assertEqual(data1["response"], data2["response"])

if __name__ == "__main__":
    unittest.main()
