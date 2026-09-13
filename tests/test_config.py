"""Unit tests for configuration and settings."""
import unittest
from pathlib import Path
from src.core.config import settings

class TestConfig(unittest.TestCase):
    def test_base_dir_resolves_to_docuchat_root(self):
        self.assertTrue(settings.BASE_DIR.exists())
        self.assertTrue((settings.BASE_DIR / "src").exists())
        self.assertEqual(settings.BASE_DIR.name, "DocuChat-AI")

    def test_documents_dir_resolves_correctly(self):
        self.assertTrue(settings.DOCUMENTS_DIR.exists())
        self.assertTrue((settings.DOCUMENTS_DIR / "MIREMS.pdf").exists())

    def test_default_settings(self):
        self.assertEqual(settings.APP_NAME, "DocuChat-AI")
        self.assertGreaterEqual(settings.MAX_RETRIES, 1)
        self.assertGreaterEqual(settings.TOP_K, 1)
        self.assertGreater(settings.SCORE_THRESHOLD, 0.0)

if __name__ == "__main__":
    unittest.main()
