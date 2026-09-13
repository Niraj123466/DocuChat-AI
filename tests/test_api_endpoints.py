"""Integration tests for FastAPI gateway endpoints."""
import unittest
from fastapi.testclient import TestClient
from src.api.app import app
from src.core.config import settings

class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        from src.core.security import JWTHandler
        cls.token = JWTHandler.create_access_token(subject="admin@docuchat.ai", role="admin")
        cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}

    def test_root_endpoint(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app_name"], "DocuChat-AI")
        self.assertEqual(data["version"], settings.APP_VERSION)

    def test_health_endpoint(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("services", data)
        self.assertIn("storage", data)
        self.assertGreaterEqual(data["storage"]["documents_count"], 1)

    def test_documents_list_endpoint(self):
        unauth = self.client.get("/api/v1/documents")
        self.assertEqual(unauth.status_code, 401)

        resp = self.client.get("/api/v1/documents", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("files", data)

    def test_whatsapp_webhook_verification_success(self):
        token = settings.WHATSAPP_VERIFY_TOKEN
        resp = self.client.get(
            f"/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test_challenge_123&hub.verify_token={token}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "test_challenge_123")

    def test_whatsapp_webhook_verification_failure(self):
        resp = self.client.get(
            "/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test_challenge_123&hub.verify_token=wrong_token"
        )
        self.assertEqual(resp.status_code, 403)

    def test_legacy_whatsapp_webhook_compatibility(self):
        token = settings.WHATSAPP_VERIFY_TOKEN
        resp = self.client.get(
            f"/webhook?hub.mode=subscribe&hub.challenge=legacy_challenge_456&hub.verify_token={token}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "legacy_challenge_456")

    def test_process_time_header(self):
        resp = self.client.get("/api/v1/health")
        self.assertIn("x-process-time", resp.headers)
        self.assertIn("x-request-id", resp.headers)

    def test_chat_endpoint_returns_citations(self):
        payload = {"message": "What is the subject of the document?"}
        resp = self.client.post("/api/v1/chat", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("response", data)
        self.assertIn("citations", data)
        self.assertIn("retry_count", data)
        self.assertIn("evaluation_passed", data)
        self.assertTrue(isinstance(data["citations"], list))

    def test_legacy_chatbot_route(self):
        payload = {"user_message": "Hello from legacy client"}
        resp = self.client.post("/chatbot", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("response", data)
        self.assertIn("citations", data)

    def test_eval_endpoints(self):
        # Test GET /api/v1/eval/latest
        resp = self.client.get("/api/v1/eval/latest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("run_id", data)
        self.assertIn("pass_rate", data)
        self.assertIn("mean_faithfulness", data)

        # Test GET /api/v1/eval/report
        resp_report = self.client.get("/api/v1/eval/report")
        self.assertEqual(resp_report.status_code, 200)
        self.assertIn("RAG Benchmark Evaluation Scorecard", resp_report.text)

if __name__ == "__main__":
    unittest.main()
