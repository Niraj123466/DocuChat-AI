"""Unit tests for the RAG evaluation framework and metrics engine."""
import unittest
from pathlib import Path
from src.evaluation.metrics import RAGEvaluator
from src.evaluation.runner import EvaluationRunner

class TestEvaluation(unittest.TestCase):
    def test_calculate_faithfulness_grounded(self):
        context = "The new health care policy gives all full-time employees comprehensive dental and vision coverage."
        answer = "Full-time employees receive comprehensive dental and vision coverage under the new policy."
        score = RAGEvaluator.calculate_faithfulness(answer, context)
        self.assertGreaterEqual(score, 0.7)

    def test_calculate_faithfulness_hallucinated(self):
        context = "Employees are entitled to 15 days of annual leave."
        # Answer introduces unsupported numbers and claims
        answer = "Employees get 45 days of paid leave and a $10,000 annual bonus."
        score = RAGEvaluator.calculate_faithfulness(answer, context)
        self.assertLess(score, 0.6)

    def test_calculate_answer_relevancy(self):
        query = "What is the procedure to request vacation leave?"
        relevant_answer = "To request vacation leave, submit the leave form to your manager at least two weeks in advance."
        irrelevant_answer = "The quick brown fox jumps over the lazy dog."

        rel_score = RAGEvaluator.calculate_answer_relevancy(query, relevant_answer)
        irrel_score = RAGEvaluator.calculate_answer_relevancy(query, irrelevant_answer)

        self.assertGreater(rel_score, irrel_score)
        self.assertGreaterEqual(rel_score, 0.6)

    def test_calculate_context_precision(self):
        expected_kws = ["vacation", "manager", "request", "two weeks"]
        retrieved_context = "Employees must submit a vacation request to their direct manager at least two weeks before."
        precision = RAGEvaluator.calculate_context_precision(expected_kws, retrieved_context)
        self.assertEqual(precision, 1.0)

    def test_load_dataset(self):
        runner = EvaluationRunner()
        cases = runner.load_dataset()
        self.assertGreaterEqual(len(cases), 5)
        self.assertIn("query", cases[0])
        self.assertIn("expected_answer", cases[0])

    def test_runner_execution_and_markdown_report(self):
        runner = EvaluationRunner()
        summary = runner.run_evaluation(max_samples=2)

        self.assertEqual(summary.total_cases, 2)
        self.assertGreaterEqual(summary.mean_faithfulness, 0.0)
        self.assertGreaterEqual(summary.mean_answer_relevancy, 0.0)

        report = runner.generate_markdown_report(summary)
        self.assertIn("RAG Benchmark Evaluation Scorecard", report)
        self.assertIn("Executive Summary", report)
        self.assertIn("Test Case Breakdown", report)

if __name__ == "__main__":
    unittest.main()
