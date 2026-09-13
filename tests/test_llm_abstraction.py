"""Unit tests for LLM provider abstraction, token budgeting, and prompt manager."""
import unittest
from src.core.llm import TokenBudgetManager, MockLLMProvider, FallbackLLMProvider, BaseLLMProvider
from src.utils.prompt_manager import PromptManager

class BrokenLLMProvider(BaseLLMProvider):
    def generate(self, messages, temperature=0.1, max_tokens=None):
        raise ConnectionError("Simulated LLM API outage.")

class TestLLMAbstraction(unittest.TestCase):
    def test_token_budget_estimation_and_truncation(self):
        short_text = "This is a brief query context."
        self.assertEqual(TokenBudgetManager.truncate_to_budget(short_text, max_tokens=50), short_text)

        long_text = "Word " * 1000
        truncated = TokenBudgetManager.truncate_to_budget(long_text, max_tokens=50)
        self.assertLess(len(truncated), len(long_text))
        self.assertIn("[Context truncated", truncated)

    def test_mock_llm_provider(self):
        mock = MockLLMProvider(predefined_response="Verified RAG Answer [Doc 1]")
        res = mock.generate([("human", "What is the policy?")])
        self.assertEqual(res, "Verified RAG Answer [Doc 1]")

    def test_fallback_llm_cascade(self):
        primary = BrokenLLMProvider()
        backup = MockLLMProvider(predefined_response="Backup response delivered.")
        cascading = FallbackLLMProvider(primary=primary, fallback=backup)

        result = cascading.generate([("human", "Test query")])
        self.assertEqual(result, "Backup response delivered.")

    def test_prompt_manager_formatting(self):
        pm = PromptManager()
        rendered = pm.get_prompt("query_agent_prompt", organization_name="AcmeCorp")
        self.assertIn("AcmeCorp", rendered)
        self.assertIn("FEW-SHOT EXAMPLES", rendered)

if __name__ == "__main__":
    unittest.main()
