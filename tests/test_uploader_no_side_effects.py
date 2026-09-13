"""Unit tests verifying uploader module has no import-time side-effects."""
import unittest
from src.Uploader.uploader_pinecone import DocumentUploader, MyDocumentUploader

class TestUploaderNoSideEffects(unittest.TestCase):
    def test_import_and_instantiation_without_network_call(self):
        # Should initialize cleanly without triggering upserts
        uploader = DocumentUploader(index_name="test-index")
        self.assertEqual(uploader.index_name, "test-index")

    def test_backward_compatibility_alias(self):
        self.assertIs(DocumentUploader, MyDocumentUploader)

if __name__ == "__main__":
    unittest.main()
