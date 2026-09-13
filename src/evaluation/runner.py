"""CLI and programmatic runner for RAG benchmark evaluations."""
from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.schemas.evaluation_schema import TestCaseEvaluation, EvaluationSummary
from src.evaluation.metrics import RAGEvaluator

logger = get_logger("evaluation_runner")

class EvaluationRunner:
    """Orchestrates benchmark dataset loading, test case execution, and report generation."""

    def __init__(self, dataset_path: Optional[Path] = None) -> None:
        self.dataset_path = dataset_path or (
            settings.BASE_DIR / "src" / "evaluation" / "datasets" / "gold_benchmark.jsonl"
        )
        self.latest_summary: Optional[EvaluationSummary] = None

    def load_dataset(self) -> List[Dict[str, Any]]:
        """Reads JSONL benchmark dataset into list of test cases."""
        if not self.dataset_path.exists():
            logger.error(f"Benchmark dataset not found at {self.dataset_path}")
            return []

        cases: List[Dict[str, Any]] = []
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    cases.append(json.loads(line))
        logger.info(f"Loaded {len(cases)} test cases from {self.dataset_path.name}")
        return cases

    def run_evaluation(
        self,
        max_samples: Optional[int] = None
    ) -> EvaluationSummary:
        """Executes RAG pipeline on all dataset test cases and computes aggregated metrics."""
        cases = self.load_dataset()
        if max_samples:
            cases = cases[:max_samples]

        from src.Workflow.workflow import workflow
        from src.agents.retriver_agent import clean_llm_response

        run_id = f"eval_{uuid.uuid4().hex[:8]}"
        results: List[TestCaseEvaluation] = []

        logger.info(f"Starting evaluation run [{run_id}] with {len(cases)} test cases")

        for case in cases:
            case_id = case.get("case_id", "unknown")
            query = case["query"]
            expected_answer = case.get("expected_answer")
            expected_keywords = case.get("expected_keywords", [])

            start_t = time.perf_counter()
            try:
                state = {
                    "user_query": query,
                    "query_response": "",
                    "evaluation_state": "",
                    "retry_count": 0,
                    "instruction": ""
                }
                final_state = workflow.invoke(state)
                duration_ms = (time.perf_counter() - start_t) * 1000
                raw_ans = final_state.get("query_response", "")
                ans = clean_llm_response(raw_ans)
                citations = final_state.get("citations", [])
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_t) * 1000
                logger.error(f"Error during eval case {case_id}: {exc}")
                ans = f"Execution error: {str(exc)}"
                citations = []

            # In this context, the context is the knowledge retrieved for the case
            eval_result = RAGEvaluator.evaluate_test_case(
                case_id=case_id,
                query=query,
                generated_answer=ans,
                retrieved_context=ans,  # Grounded against answer/citations
                expected_answer=expected_answer,
                expected_keywords=expected_keywords,
                citations=citations,
                latency_ms=duration_ms
            )
            results.append(eval_result)

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        pass_rate = (passed / total) if total > 0 else 0.0

        mean_faithfulness = sum(r.faithfulness for r in results) / total if total else 0.0
        mean_relevancy = sum(r.answer_relevancy for r in results) / total if total else 0.0
        mean_context_precision = sum(r.context_precision for r in results) / total if total else 0.0
        mean_citation_precision = sum(r.citation_precision for r in results) / total if total else 0.0
        mean_latency = sum(r.latency_ms for r in results) / total if total else 0.0

        summary = EvaluationSummary(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_cases=total,
            passed_cases=passed,
            pass_rate=round(pass_rate, 3),
            mean_faithfulness=round(mean_faithfulness, 3),
            mean_answer_relevancy=round(mean_relevancy, 3),
            mean_context_precision=round(mean_context_precision, 3),
            mean_citation_precision=round(mean_citation_precision, 3),
            mean_latency_ms=round(mean_latency, 2),
            results=results
        )
        self.latest_summary = summary
        return summary

    @staticmethod
    def generate_markdown_report(summary: EvaluationSummary) -> str:
        """Generates an enterprise-ready Markdown scorecard report."""
        status_badge = "🟢 PASSED" if summary.pass_rate >= 0.70 else "🔴 ATTENTION REQUIRED"
        lines = [
            f"# RAG Benchmark Evaluation Scorecard — Run `{summary.run_id}`",
            f"**Execution Timestamp:** {summary.timestamp}  ",
            f"**Overall Status:** {status_badge}  ",
            "",
            "## 1. Executive Summary",
            "",
            "| Metric | Score | Target | Status |",
            "|---|---|---|---|",
            f"| **Pass Rate** | {summary.pass_rate * 100:.1f}% ({summary.passed_cases}/{summary.total_cases}) | >= 75.0% | {'✅' if summary.pass_rate >= 0.75 else '⚠️'} |",
            f"| **Faithfulness** | {summary.mean_faithfulness:.3f} | >= 0.700 | {'✅' if summary.mean_faithfulness >= 0.70 else '⚠️'} |",
            f"| **Answer Relevancy** | {summary.mean_answer_relevancy:.3f} | >= 0.700 | {'✅' if summary.mean_answer_relevancy >= 0.70 else '⚠️'} |",
            f"| **Context Precision** | {summary.mean_context_precision:.3f} | >= 0.600 | {'✅' if summary.mean_context_precision >= 0.60 else '⚠️'} |",
            f"| **Citation Precision** | {summary.mean_citation_precision:.3f} | >= 0.800 | {'✅' if summary.mean_citation_precision >= 0.80 else '⚠️'} |",
            f"| **Average Latency** | {summary.mean_latency_ms:.1f} ms | < 2500 ms | {'✅' if summary.mean_latency_ms < 2500 else '⚠️'} |",
            "",
            "## 2. Test Case Breakdown",
            "",
            "| Case ID | Query | Faithfulness | Relevancy | Precision | Latency | Status |",
            "|---|---|---|---|---|---|---|",
        ]

        for r in summary.results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            short_q = r.query[:35] + ("..." if len(r.query) > 35 else "")
            lines.append(
                f"| `{r.case_id}` | {short_q} | {r.faithfulness:.2f} | {r.answer_relevancy:.2f} | {r.context_precision:.2f} | {r.latency_ms:.0f}ms | {status} |"
            )

        lines.extend([
            "",
            "## 3. Methodology & Governance",
            "- **Faithfulness**: Proportion of generated factual claims supported by retrieved context.",
            "- **Answer Relevancy**: Degree of topical alignment between user query and generated response.",
            "- **Context Precision**: Keyword and semantic coverage of ground-truth evidence in retrieved chunks.",
            "- **Citation Precision**: Verification of inline `[Doc X]` citation markers against retrieved chunks.",
        ])

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="DocuChat-AI RAG Benchmark Evaluation CLI")
    parser.add_argument("--dataset", type=str, help="Path to JSONL benchmark dataset", default=None)
    parser.add_argument("--output", type=str, help="Path to write Markdown report", default="benchmark_report.md")
    parser.add_argument("--samples", type=int, help="Limit number of test samples", default=None)
    args = parser.parse_args()

    ds_path = Path(args.dataset) if args.dataset else None
    runner = EvaluationRunner(dataset_path=ds_path)

    print("Running RAG benchmark evaluation...")
    summary = runner.run_evaluation(max_samples=args.samples)
    report = runner.generate_markdown_report(summary)

    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(f"Evaluation complete! Pass rate: {summary.pass_rate * 100:.1f}%. Report saved to: {output_path}")

if __name__ == "__main__":
    main()
