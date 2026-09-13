# RAG Benchmark Evaluation Scorecard — Run `eval_1bb6d1b3`
**Execution Timestamp:** 2026-09-12T11:07:41.818088+00:00  
**Overall Status:** 🟢 PASSED  

## 1. Executive Summary

| Metric | Score | Target | Status |
|---|---|---|---|
| **Pass Rate** | 100.0% (3/3) | >= 75.0% | ✅ |
| **Faithfulness** | 1.000 | >= 0.700 | ✅ |
| **Answer Relevancy** | 0.686 | >= 0.700 | ⚠️ |
| **Context Precision** | 0.150 | >= 0.600 | ⚠️ |
| **Citation Precision** | 0.300 | >= 0.800 | ⚠️ |
| **Average Latency** | 56.5 ms | < 2500 ms | ✅ |

## 2. Test Case Breakdown

| Case ID | Query | Faithfulness | Relevancy | Precision | Latency | Status |
|---|---|---|---|---|---|---|
| `eval_001` | What did the BCGEU member post on s... | 1.00 | 0.72 | 0.20 | 97ms | ✅ PASS |
| `eval_002` | What initiative did the federal gov... | 1.00 | 0.65 | 0.00 | 34ms | ✅ PASS |
| `eval_003` | How many days of paid annual vacati... | 1.00 | 0.69 | 0.25 | 38ms | ✅ PASS |

## 3. Methodology & Governance
- **Faithfulness**: Proportion of generated factual claims supported by retrieved context.
- **Answer Relevancy**: Degree of topical alignment between user query and generated response.
- **Context Precision**: Keyword and semantic coverage of ground-truth evidence in retrieved chunks.
- **Citation Precision**: Verification of inline `[Doc X]` citation markers against retrieved chunks.