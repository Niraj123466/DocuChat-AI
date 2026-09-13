"""Schemas for RAG evaluation, benchmarks, and quality scorecards."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class EvaluationOutput(BaseModel):
    """Legacy evaluation output schema."""
    has_hallucinations: bool = False
    citations_complete: bool = True
    evaluation_score: float = 5.0
    evaluation_feedback: str = ""

class TestCaseEvaluation(BaseModel):
    """Evaluation result for an individual benchmark test case."""
    case_id: str = Field(..., description="Unique test case identifier")
    query: str = Field(..., description="Test query string")
    expected_answer: Optional[str] = Field(None, description="Gold reference answer")
    generated_answer: str = Field(..., description="Model generated response")
    faithfulness: float = Field(..., ge=0.0, le=1.0, description="Faithfulness / grounding score")
    answer_relevancy: float = Field(..., ge=0.0, le=1.0, description="Answer relevancy score")
    context_precision: float = Field(..., ge=0.0, le=1.0, description="Context retrieval precision")
    citation_precision: float = Field(default=1.0, ge=0.0, le=1.0, description="Citation accuracy score")
    latency_ms: float = Field(..., description="Execution latency in milliseconds")
    passed: bool = Field(..., description="Overall test case pass status")
    critique: Optional[str] = Field(None, description="Diagnostic critique")

class EvaluationSummary(BaseModel):
    """Aggregated scorecard for an entire benchmark evaluation run."""
    run_id: str
    timestamp: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    mean_faithfulness: float
    mean_answer_relevancy: float
    mean_context_precision: float
    mean_citation_precision: float
    mean_latency_ms: float
    results: List[TestCaseEvaluation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)