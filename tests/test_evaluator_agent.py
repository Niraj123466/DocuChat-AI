"""Unit tests for Evaluator Agent node."""
import unittest
from src.agents.evaluator_agent import evaluator_agent
from src.core.config import settings

class TestEvaluatorAgent(unittest.TestCase):
    def test_clean_response_passes(self):
        state = {
            "user_query": "What is the policy?",
            "query_response": "This is a clean and professional response.",
            "evaluation_state": "",
            "retry_count": 0,
            "instruction": ""
        }
        res = evaluator_agent(state)
        self.assertEqual(res["evaluation_state"], "True")
        self.assertEqual(res["retry_count"], 0)
        self.assertEqual(res["instruction"], "")
        self.assertEqual(res["query_response"], state["query_response"])

    def test_max_retries_termination(self):
        state = {
            "user_query": "Test query",
            "query_response": "Offensive output",
            "evaluation_state": "",
            "retry_count": settings.MAX_RETRIES,
            "instruction": ""
        }
        res = evaluator_agent(state)
        self.assertEqual(res["evaluation_state"], "True")
        self.assertEqual(res["retry_count"], settings.MAX_RETRIES)
        self.assertIn("could not formulate", res["query_response"])

    def test_retry_count_preserved(self):
        state = {
            "user_query": "Explain quantum computing",
            "query_response": "Quantum computers use qubits.",
            "evaluation_state": "",
            "retry_count": 2,
            "instruction": "Previous instruction"
        }
        res = evaluator_agent(state)
        self.assertEqual(res["retry_count"], 2)

if __name__ == "__main__":
    unittest.main()
