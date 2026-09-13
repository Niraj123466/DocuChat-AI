"""Unit tests for the Citation Engine."""
import unittest
from src.rag.rerankers.base import RankedChunk
from src.rag.citation import CitationEngine

class TestCitationEngine(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            RankedChunk(content="Annual vacation entitlement is 25 days.", source="handbook.pdf", chunk_id=101, score=0.92, page_number=4),
            RankedChunk(content="Health insurance covers dental and optical care.", source="benefits.pdf", chunk_id=102, score=0.85, page_number=8),
        ]

    def test_format_context_for_prompt(self):
        formatted = CitationEngine.format_context_for_prompt(self.chunks)
        self.assertIn("[Doc 1: handbook.pdf | Page 4]", formatted)
        self.assertIn("[Doc 2: benefits.pdf | Page 8]", formatted)
        self.assertIn("Annual vacation entitlement", formatted)

    def test_extract_citations_explicit_tags(self):
        llm_response = "Employees receive 25 days of vacation [Doc 1] and dental coverage [Doc 2]."
        citations = CitationEngine.extract_citations(llm_response, self.chunks)

        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0]["doc_index"], 1)
        self.assertEqual(citations[0]["source"], "handbook.pdf")
        self.assertEqual(citations[0]["chunk_id"], "101")
        self.assertEqual(citations[0]["page_number"], 4)
        self.assertIn("Annual vacation", citations[0]["text_snippet"])

        self.assertEqual(citations[1]["doc_index"], 2)
        self.assertEqual(citations[1]["source"], "benefits.pdf")
        self.assertEqual(citations[1]["chunk_id"], "102")

    def test_extract_citations_single_tag(self):
        llm_response = "Vacation is 25 days per year [Doc 1]."
        citations = CitationEngine.extract_citations(llm_response, self.chunks)

        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["doc_index"], 1)

    def test_extract_citations_empty(self):
        self.assertEqual(CitationEngine.extract_citations("", self.chunks), [])
        self.assertEqual(CitationEngine.extract_citations("Some text", []), [])

if __name__ == "__main__":
    unittest.main()
