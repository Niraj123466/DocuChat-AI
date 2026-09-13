"""RAG Evaluation Metrics Engine: Faithfulness, Answer Relevancy, and Context Precision."""
from __future__ import annotations

import re
import math
from typing import List, Dict, Any, Optional

from src.schemas.evaluation_schema import TestCaseEvaluation
from src.core.logging import get_logger

logger = get_logger("evaluation_metrics")

class RAGEvaluator:
    """Evaluates RAG pipeline outputs across standard MLOps quality metrics."""

    @classmethod
    def calculate_faithfulness(cls, answer: str, context: str) -> float:
        """Measures whether the generated answer is strictly grounded in retrieved context (0.0 to 1.0)."""
        if not answer or not answer.strip():
            return 0.0

        if not context or "No relevant context" in context:
            # If the answer appropriately acknowledges lack of context, it is faithful
            if any(refusal in answer.lower() for refusal in ["cannot find", "not able to help", "apologize", "no verified"]):
                return 1.0
            return 0.2  # Hallucinated answer without context

        # Extract non-stopword tokens (3+ chars)
        stopwords = {"the", "and", "for", "that", "this", "with", "from", "are", "was", "were", "been", "have", "has"}
        ans_tokens = [t for t in re.findall(r"\b[a-zA-Z]{3,}\b", answer.lower()) if t not in stopwords]
        ctx_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", context.lower()))

        if not ans_tokens:
            return 1.0

        supported = [t for t in ans_tokens if t in ctx_tokens]
        coverage = len(supported) / len(ans_tokens)

        # Penalize if answer claims specific numbers or dates not found in context
        ans_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", answer))
        ctx_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", context))
        unsupported_nums = ans_numbers - ctx_numbers
        if unsupported_nums:
            coverage *= max(0.5, 1.0 - (len(unsupported_nums) * 0.15))

        return round(min(1.0, max(0.0, float(coverage))), 3)

    @classmethod
    def calculate_answer_relevancy(cls, query: str, answer: str) -> float:
        """Measures how well the generated answer addresses the question (0.0 to 1.0)."""
        if not query or not answer:
            return 0.0

        q_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))
        a_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", answer.lower()))

        if not q_tokens:
            return 0.8

        overlap = q_tokens.intersection(a_tokens)
        query_coverage = len(overlap) / len(q_tokens)

        # Reward concise, direct answers (> 20 chars, < 1500 chars)
        length_penalty = 1.0
        if len(answer) < 20:
            length_penalty = 0.5
        elif len(answer) > 2000:
            length_penalty = 0.85

        score = (query_coverage * 0.7 + 0.3) * length_penalty
        return round(min(1.0, max(0.0, float(score))), 3)

    @classmethod
    def calculate_context_precision(
        cls,
        expected_keywords: Optional[List[str]],
        retrieved_context: str
    ) -> float:
        """Measures whether the retrieved context contains the necessary ground truth keywords."""
        if not expected_keywords:
            return 1.0
        if not retrieved_context:
            return 0.0

        ctx_lower = retrieved_context.lower()
        matched = sum(1 for kw in expected_keywords if kw.lower() in ctx_lower)
        precision = matched / len(expected_keywords)
        return round(min(1.0, max(0.0, float(precision))), 3)

    @classmethod
    def calculate_citation_precision(
        cls,
        citations: List[Dict[str, Any]],
        answer: str
    ) -> float:
        """Measures whether citations referenced in the answer are valid and present."""
        if not citations:
            # If answer didn't claim citations and none were produced
            if "[doc" not in answer.lower():
                return 1.0
            return 0.3  # Mentioned citations but none extracted

        # Check if citations correspond to actual markers
        valid_citations = 0
        for c in citations:
            doc_idx = c.get("doc_index")
            if f"[doc {doc_idx}]" in answer.lower() or f"[{doc_idx}]" in answer:
                valid_citations += 1

        score = (valid_citations / len(citations)) if citations else 1.0
        return round(min(1.0, max(0.0, float(score))), 3)

    @classmethod
    def evaluate_test_case(
        cls,
        case_id: str,
        query: str,
        generated_answer: str,
        retrieved_context: str,
        expected_answer: Optional[str] = None,
        expected_keywords: Optional[List[str]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        latency_ms: float = 150.0
    ) -> TestCaseEvaluation:
        """Runs full suite of RAG metrics on an individual test case."""
        faithfulness = cls.calculate_faithfulness(generated_answer, retrieved_context)
        relevancy = cls.calculate_answer_relevancy(query, generated_answer)
        context_precision = cls.calculate_context_precision(expected_keywords, retrieved_context)
        citation_precision = cls.calculate_citation_precision(citations or [], generated_answer)

        # A test case passes if faithfulness >= 0.50 and relevancy >= 0.50
        passed = faithfulness >= 0.50 and relevancy >= 0.50

        critique = None
        if not passed:
            reasons = []
            if faithfulness < 0.50:
                reasons.append(f"Low faithfulness ({faithfulness})")
            if relevancy < 0.50:
                reasons.append(f"Low relevancy ({relevancy})")
            critique = "Failed: " + ", ".join(reasons)

        return TestCaseEvaluation(
            case_id=case_id,
            query=query,
            expected_answer=expected_answer,
            generated_answer=generated_answer,
            faithfulness=faithfulness,
            answer_relevancy=relevancy,
            context_precision=context_precision,
            citation_precision=citation_precision,
            latency_ms=round(latency_ms, 2),
            passed=passed,
            critique=critique
        )
