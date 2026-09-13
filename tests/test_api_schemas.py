"""Unit tests verifying API models, schemas, and routing constructs."""
import unittest
from src.api.v1.chat import ChatRequest, ChatResponse
from src.api.v1.documents import DocumentItem, DocumentListResponse

class TestApiSchemas(unittest.TestCase):
    def test_chat_request_validations(self):
        req = ChatRequest(user_message="Hello world")
        self.assertEqual(req.get_query(), "Hello world")

        req_alt = ChatRequest(message="Alternative field")
        self.assertEqual(req_alt.get_query(), "Alternative field")

        req_empty = ChatRequest(user_message="   ")
        with self.assertRaises(ValueError):
            req_empty.get_query()

    def test_chat_response_construction(self):
        resp = ChatResponse(
            response="Test response",
            retry_count=1,
            evaluation_passed=True,
            metadata={"latency_ms": 120}
        )
        self.assertEqual(resp.response, "Test response")
        self.assertEqual(resp.retry_count, 1)
        self.assertTrue(resp.evaluation_passed)
        self.assertEqual(resp.metadata["latency_ms"], 120)

    def test_document_list_response(self):
        item = DocumentItem(name="MIREMS.pdf", size_bytes=42064, modified_at="2026-09-12T10:00:00Z")
        doc_resp = DocumentListResponse(documents_dir="/app/documents", total_files=1, files=[item])
        self.assertEqual(doc_resp.total_files, 1)
        self.assertEqual(doc_resp.files[0].name, "MIREMS.pdf")

if __name__ == "__main__":
    unittest.main()
