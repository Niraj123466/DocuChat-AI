"""Unit tests for the Reranking subsystem."""
import unittest
from src.rag.rerankers.base import RankedChunk
from src.rag.rerankers.cross_encoder import CrossEncoderReranker

class TestReranker(unittest.TestCase):
    def setUp(self):
        self.reranker = CrossEncoderReranker(min_score=0.1)
        self.chunks = [
            RankedChunk(content="The weather today is sunny and pleasant in California.", source="weather.pdf", chunk_id=1),
            RankedChunk(content="Quantum supremacy was achieved using superconducting qubits.", source="physics.pdf", chunk_id=2),
            RankedChunk(content="A quantum computer utilizes superposition and entanglement for computation.", source="quantum.pdf", chunk_id=3),
        ]

    def test_rerank_orders_by_relevance(self):
        query = "How do quantum computers work?"
        reranked = self.reranker.rerank(query, self.chunks, top_n=3)

        self.assertGreaterEqual(len(reranked), 1)
        # Quantum-related chunks should be ranked higher than the weather chunk
        top_chunk = reranked[0]
        self.assertIn("quantum", top_chunk.content.lower())
        # The lowest ranked or excluded should be the weather chunk
        if len(reranked) == 3:
            self.assertEqual(reranked[-1].chunk_id, 1)

    def test_rerank_empty_list(self):
        result = self.reranker.rerank("any query", [], top_n=5)
        self.assertEqual(result, [])

    def test_rerank_respects_top_n(self):
        query = "quantum"
        reranked = self.reranker.rerank(query, self.chunks, top_n=2)
        self.assertLessEqual(len(reranked), 2)

if __name__ == "__main__":
    unittest.main()
