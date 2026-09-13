# DocuChat-AI — Enterprise Production Architecture (Target Specification)
**Version:** 2.0.0  
**Status:** Approved Target Blueprint  
**Authors:** Senior AI/ML & Platform Architecture Team  

---

## 1. Executive Architecture Overview

DocuChat-AI is an enterprise-grade, agentic **Retrieval-Augmented Generation (RAG)** platform designed to ingest unstructured documents, perform high-precision hybrid/dense semantic search with reranking, execute multi-step reasoning workflows via **LangGraph**, enforce strict AI safety and guardrails, and deliver grounded, cited responses across both **REST APIs** and **WhatsApp webhooks**.

### Core Architecture Principles
1. **Groundedness & Zero-Hallucination Enforced by Design**: Every LLM generation is conditioned on verified vector retrieval, reranked by cross-encoders, and evaluated by an autonomous guard node before reaching the user.
2. **Layered Separation of Concerns**: Clean hexagonal/layered architecture decoupling Presentation (FastAPI), Orchestration (LangGraph), Knowledge (Pinecone/Docling), Security (Guardrails/JWT), and Persistence (PostgreSQL/Redis).
3. **Resilience & Self-Correction**: Agentic feedback loops retry queries with query-rewriting if context retrieval or safety validation fails, bounded by configurable maximum retry limits.
4. **End-to-End Observability**: Distributed tracing via OpenTelemetry, metrics exported to Prometheus, and structured audit logs tracking prompt tokens, generation latency, and safety verdicts.
5. **Production MLOps**: Continuous evaluation pipelines (LLM-as-a-judge & Ragas metrics) validating retrieval precision, faithfulness, and answer relevancy against gold standard benchmarks.

---

## 2. End-to-End System Topology

```mermaid
flowchart TD
    subgraph Ingress["Layer 1: Ingress & API Gateway (FastAPI)"]
        CLIENT[Web Frontend / Mobile] -->|HTTPS REST / SSE| GATEWAY[FastAPI Application Gateway]
        WA[WhatsApp / Meta Webhook] -->|HMAC-SHA256 Signed POST| WA_HANDLER[WhatsApp Webhook Router]
        WA_HANDLER --> GATEWAY
        GATEWAY --> CORS[CORS & Security Headers]
        CORS --> RATELIMIT[Token Bucket Rate Limiter - Redis / SlowAPI]
        RATELIMIT --> AUTH[JWT & RBAC Middleware]
    end

    subgraph Security["Layer 2: AI Security & Guardrails"]
        AUTH --> IN_GUARD[Input Guardrails: Injection Detection, PII & Profanity]
        IN_GUARD -->|Blocked| REJECT[400 Bad Request / Safe Fallback]
    end

    subgraph Orchestration["Layer 3: Agentic Orchestration (LangGraph StateGraph)"]
        IN_GUARD -->|Sanitized State| GRAPH_ENTRY([Workflow Entrypoint])
        GRAPH_ENTRY --> ROUTER{Intent Router}
        ROUTER -->|Document Query| RETRIEVER_NODE[Retriever Agent Node]
        ROUTER -->|General Conversation| GENERAL_NODE[Direct LLM Node]
        
        RETRIEVER_NODE --> RERANK_NODE[Cross-Encoder Reranker Node]
        RERANK_NODE --> GENERATOR_NODE[Contextual Generator Node]
        GENERATOR_NODE --> EVALUATOR_NODE[Evaluator & Grounding Guard Node]
        
        EVALUATOR_NODE -->|Failed & Retries < Max| REWRITE_NODE[Query Reformulator Node]
        REWRITE_NODE --> RETRIEVER_NODE
        EVALUATOR_NODE -->|Max Retries Exceeded| FALLBACK_NODE[Grounded Graceful Fallback]
        EVALUATOR_NODE -->|Passed Verification| OUT_GUARD[Output Safety & Citation Formatter]
    end

    subgraph Knowledge["Layer 4: RAG, Embeddings & Vector Store"]
        DOCS[Uploaded Documents: PDF, DOCX, TXT] --> INGEST_API[Document Ingestion Pipeline]
        INGEST_API --> DOCLING[Docling Markdown & Table Parser]
        DOCLING --> CHUNKER[Semantic Recursive Chunker]
        CHUNKER --> EMBEDDER[HuggingFace sentence-transformers all-MiniLM-L6-v2]
        EMBEDDER --> PINECONE[(Pinecone Vector DB - Inverted Index & Metadata)]
        
        RETRIEVER_NODE -.->|Top-K Query| PINECONE
        RERANK_NODE -.->|Cross-Encoder MS-Marco| RERANK_MODEL[Cross-Encoder Reranker]
    end

    subgraph Persistence["Layer 5: Persistence & Cache Layer"]
        AUTH -.-> DB[(PostgreSQL: Users, Convos, Audit)]
        OUT_GUARD -.-> DB
        GATEWAY -.-> REDIS[(Redis: Semantic Cache, Session, Rate-Limits)]
    end

    subgraph Observability["Layer 6: Observability & MLOps"]
        GATEWAY -.-> OTEL[OpenTelemetry Tracing]
        GATEWAY -.-> PROM[Prometheus Metrics]
        GATEWAY -.-> STRUCTLOG[Structlog JSON Logger]
        EVAL_CLI[Offline Evaluation CLI] -.-> RAGAS[Ragas / LLM-as-a-Judge Pipeline]
    end

    OUT_GUARD --> RESPONSE[Validated Cited Response Stream]
```

---

## 3. Detailed Subsystem Specifications

### 3.1 Layer 1: Ingress & API Gateway (FastAPI)
- **Unified Application Core**: Eliminate code duplication between `main.py` and `chatbotapi.py`. A single unified FastAPI application instance configured in `src/api/app.py` exposes modular APIRouters under `/api/v1`:
  - `/api/v1/auth`: User registration, login, token refresh, and profile management.
  - `/api/v1/chat`: Streaming and standard chat endpoints, conversation thread management.
  - `/api/v1/documents`: Document upload, indexing status, deletion, and chunk inspection.
  - `/api/v1/eval`: Trigger evaluation runs and view historical quality metrics.
  - `/api/v1/health`: Liveness and readiness probes checking DB, Redis, and Pinecone health.
  - `/webhooks/whatsapp`: Secure webhook verification (`GET`) and message ingestion (`POST`).
- **Standardized Exception Handling**: Implements RFC 7807 (Problem Details for HTTP APIs) with consistent error schemas:
  ```json
  {
    "type": "https://docuchat.ai/errors/retrieval-failed",
    "title": "Document Retrieval Error",
    "status": 502,
    "detail": "Vector index timed out while querying namespace 'default'.",
    "instance": "/api/v1/chat/message",
    "timestamp": "2026-09-12T10:50:00Z"
  }
  ```
- **WhatsApp Webhook Security**: Replaces hardcoded verification tokens with environment variables (`WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`). Inbound messages undergo cryptographic HMAC-SHA256 signature verification (`X-Hub-Signature-256`) to guarantee authenticity.

---

### 3.2 Layer 2: AI Security & Guardrails

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Gateway as FastAPI Gateway
    participant Guard as Guardrails Engine
    participant Agent as LangGraph Workflow
    participant LLM as Google Gemini LLM

    User->>Gateway: POST /api/v1/chat/message (Prompt)
    Gateway->>Guard: Validate Input (Injection Heuristics + Vector Similarity Check)
    alt Prompt Injection or Malicious Pattern Detected
        Guard-->>Gateway: Flagged: Insecure Intent
        Gateway-->>User: 400 Bad Request ("Prompt violates safety policy.")
    else Input Sanitized & Approved
        Guard->>Agent: Execute State Graph
        Agent->>LLM: Generate Grounded Answer
        LLM-->>Agent: Raw Response
        Agent->>Guard: Validate Output (Hallucination Check, Profanity, PII)
        alt Ungrounded / Toxic Content Detected
            Guard-->>Agent: Rejection Signal (Trigger Retry or Fallback)
        else Output Validated
            Guard-->>Gateway: Verified Response + Source Citations
            Gateway-->>User: 200 OK (Clean Response + Citations)
        end
    end
```

- **OWASP Top 10 for LLM Defense Matrix**:
  1. **LLM01: Prompt Injection**: Dual-phase filtering (regex heuristic for jailbreaks, plus embedding cosine distance against known jailbreak pattern vectors).
  2. **LLM02: Sensitive Information Disclosure**: PII scrubbing (regex patterns for emails, SSNs, credit cards, phone numbers, and secrets) prior to vector indexing and LLM prompt construction.
  3. **LLM06: Excessive Agency**: LangGraph nodes execute with isolated, immutable tool permissions. SimpleExecutor cannot execute arbitrary shell or DB commands.
  4. **LLM09: Overreliance / Hallucination**: Evaluator node cross-checks generated sentences against retrieved context chunks using NLI (Natural Language Inference) or LLM evaluation before emitting the payload.

---

### 3.3 Layer 3: LangGraph Agentic Orchestration

The system utilizes a directed acyclic graph (with conditional retry cycles) implemented with LangGraph `StateGraph`.

```mermaid
stateDiagram-v2
    [*] --> IngestionValidation
    IngestionValidation --> IntentRouter
    
    IntentRouter --> DirectResponseNode: Generic query / Greeting
    IntentRouter --> RetrieverNode: Knowledge query
    
    RetrieverNode --> RerankerNode: Top-K Chunks Retrieved (e.g. K=10)
    RerankerNode --> GeneratorNode: Top-N Re-scored Chunks (e.g. N=3)
    
    GeneratorNode --> EvaluatorNode: Generated Answer + Citations
    
    EvaluatorNode --> EvaluatorDecision: Assess Groundedness & Safety
    
    EvaluatorDecision --> ValidatedOutputNode: Score >= 0.7 & Safe
    EvaluatorDecision --> QueryReformulatorNode: Score < 0.7 & Retry < 3
    EvaluatorDecision --> FallbackNode: Score < 0.7 & Retry >= 3
    
    QueryReformulatorNode --> RetrieverNode: Reformulated Query
    FallbackNode --> [*]: "I cannot verify this information in the provided documents."
    DirectResponseNode --> [*]
    ValidatedOutputNode --> [*]
```

#### Graph State Schema (`src/schemas/graph_state.py`)
```python
from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

class DocumentChunk(TypedDict):
    chunk_id: str
    source_document: str
    page_number: Optional[int]
    content: str
    relevance_score: float

class EvaluationResult(TypedDict):
    groundedness_score: float
    relevance_score: float
    is_safe: bool
    critique: Optional[str]

class AgentState(TypedDict):
    conversation_id: str
    user_id: str
    raw_query: str
    reformulated_query: Optional[str]
    retrieved_documents: List[DocumentChunk]
    generated_answer: Optional[str]
    citations: List[Dict[str, Any]]
    evaluation: Optional[EvaluationResult]
    retry_count: int
    max_retries: int
    error: Optional[str]
```

---

### 3.4 Layer 4: Advanced RAG Subsystem

1. **Document Ingestion & Chunking**:
   - Uses `docling` to extract rich hierarchical structure, markdown tables, and headers from PDF documents.
   - Text splitter: `RecursiveCharacterTextSplitter` configured with chunk size of 512 tokens and 64-token overlap, preserving header breadcrumbs in chunk metadata.
2. **Dense Vector Search**:
   - Embeddings: HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, normalized).
   - Pinecone Vector Database with namespace isolation per workspace/user.
   - Initial retrieval query requests `top_k = 10`.
3. **Cross-Encoder Reranking**:
   - Retrieved chunks pass through a secondary cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
   - The top 3-4 chunks with score above threshold (> 0.25) are packed into the generation prompt, dramatically improving answer relevance and eliminating context dilution.
4. **Deterministic Citation Tracking**:
   - Chunks are numbered in the prompt: `[Doc 1: {source}, p.{page}]`.
   - The LLM is instructed via few-shot prompts to cite inline tags like `[Doc 1]`.
   - The citation extractor matches tags against `DocumentChunk` metadata to produce verified clickable citations in the API response.

---

### 3.5 Layer 5: Data & Persistence

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : owns
    CONVERSATIONS ||--o{ MESSAGES : contains
    CONVERSATIONS ||--o{ EVALUATIONS : assesses
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : contains

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string role "admin | user | analyst"
        datetime created_at
        boolean is_active
    }

    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        string title
        datetime created_at
        datetime updated_at
    }

    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        string sender "user | assistant | system"
        text content
        jsonb citations
        jsonb metadata
        datetime created_at
    }

    DOCUMENTS {
        uuid id PK
        string filename
        string file_hash UK
        string content_type
        integer file_size
        string pinecone_namespace
        datetime uploaded_at
    }

    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        string chunk_id UK
        integer page_number
        text chunk_text
        jsonb metadata
    }

    EVALUATIONS {
        uuid id PK
        uuid message_id FK
        float faithfulness
        float answer_relevancy
        float context_precision
        boolean profanity_flag
        datetime evaluated_at
    }
```

- **Redis Multi-Tier Caching**:
  - **Query Cache**: Exact SHA-256 hash match on query string + document namespace stores the generated response for 1 hour (TTL).
  - **Embedding Cache**: Cached 384-dim embedding vectors for frequent queries avoid unnecessary local inference overhead.
  - **Rate Limit Counters**: Token-bucket sliding window state keyed by client IP / user ID.

---

### 3.6 Layer 6: Observability, Tracing & Model Evaluation

```mermaid
flowchart LR
    subgraph ObservabilityStack["Full-Stack Observability"]
        APP[FastAPI & LangGraph Engine] -->|Traces: Spans, Latencies| OTEL_EXP[OpenTelemetry Collector]
        APP -->|Metrics: Requests, Tokens, Errors| PROM_EXP[Prometheus Scrape Endpoint]
        APP -->|JSON Structured Logs| LOG_EXP[Stdout / Structlog]
        
        OTEL_EXP --> JAEGER[Jaeger / Grafana Tempo]
        PROM_EXP --> GRAFANA[Grafana Dashboards]
    end

    subgraph MLOpsEval["MLOps Continuous Evaluation"]
        TEST_SET[(Gold Benchmark Dataset: Q/Context/GroundTruth)] --> EVAL_RUNNER[Evaluation Runner CLI]
        EVAL_RUNNER --> RAGAS_ENGINE[Ragas / LLM-as-a-Judge]
        RAGAS_ENGINE --> FAITHFULNESS[Faithfulness Score]
        RAGAS_ENGINE --> RELEVANCY[Answer Relevancy Score]
        RAGAS_ENGINE --> PRECISION[Context Precision Score]
        RAGAS_ENGINE --> REPORT[Eval Benchmark Markdown Report]
    end
```

#### Key Prometheus Metrics
- `docuchat_requests_total{endpoint, method, status}`: API request throughput and HTTP status distributions.
- `docuchat_llm_latency_seconds{model, node}`: Histogram of LLM generation duration per agent node.
- `docuchat_retrieval_latency_seconds`: Latency breakdown for Pinecone vector query and cross-encoder rerank.
- `docuchat_rag_faithfulness_ratio`: Running average of grounding / faithfulness score evaluated across requests.
- `docuchat_token_usage_total{type="input|output", model}`: Token consumption tracking for cost modeling.

---

## 4. Target Clean Repository Directory Structure

```
DocuChat-AI/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Automated testing, linting, type-checking
│       └── eval.yml               # Automated RAG regression benchmark run
├── src/
│   ├── api/                       # API layer (FastAPI)
│   │   ├── __init__.py
│   │   ├── app.py                 # Application factory, lifespan, CORS, middleware
│   │   ├── dependencies.py        # Auth, DB session, Redis, service dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # Unified v1 router
│   │       ├── auth.py            # Authentication & RBAC endpoints
│   │       ├── chat.py            # Chat & streaming endpoints
│   │       ├── documents.py       # Document upload & management endpoints
│   │       ├── eval.py            # Model evaluation inspection endpoints
│   │       ├── health.py          # Liveness & readiness probes
│   │       └── whatsapp.py        # Secure WhatsApp webhook endpoint
│   ├── core/                      # System configuration & foundational utilities
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic v2 BaseSettings with typed env vars
│   │   ├── logging.py             # Structlog configuration with JSON formatters
│   │   ├── telemetry.py           # OpenTelemetry & Prometheus instrumentation
│   │   └── security.py           # Password hashing, JWT signing & verification
│   ├── guardrails/                # AI Safety & Security
│   │   ├── __init__.py
│   │   ├── input_guard.py         # Prompt injection & jailbreak detection
│   │   ├── output_guard.py        # Hallucination, PII & profanity verification
│   │   └── sanitizers.py          # Text sanitization & escaping routines
│   ├── rag/                       # RAG & Knowledge Retrieval Subsystem
│   │   ├── __init__.py
│   │   ├── loaders/               # Document ingestion strategies (Docling, PDF)
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── docling_loader.py
│   │   ├── chunking/              # Chunking and text splitting logic
│   │   │   ├── __init__.py
│   │   │   └── semantic_chunker.py
│   │   ├── embeddings/            # Embedding provider abstraction
│   │   │   ├── __init__.py
│   │   │   └── sentence_transformer.py
│   │   ├── vector_stores/         # Vector index strategies
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── pinecone_store.py
│   │   ├── rerankers/             # Cross-encoder rerankers
│   │   │   ├── __init__.py
│   │   │   └── cross_encoder.py
│   │   └── citation.py            # Citation extraction & link engine
│   ├── workflow/                  # LangGraph Agentic Orchestration
│   │   ├── __init__.py
│   │   ├── graph.py               # StateGraph compilation & edge definitions
│   │   ├── state.py               # AgentState TypedDict and validation models
│   │   ├── nodes/                 # Individual workflow nodes
│   │   │   ├── __init__.py
│   │   │   ├── router_node.py
│   │   │   ├── retriever_node.py
│   │   │   ├── reranker_node.py
│   │   │   ├── generator_node.py
│   │   │   ├── evaluator_node.py
│   │   │   └── fallback_node.py
│   │   └── prompts/               # Prompt templates & versioned YAML specs
│   │       ├── prompts.yml
│   │       └── prompt_manager.py
│   ├── db/                        # Database ORM & Migrations
│   │   ├── __init__.py
│   │   ├── session.py             # Async SQLAlchemy engine & session factory
│   │   ├── models/                # SQLAlchemy models (User, Conversation, Message, etc.)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── document.py
│   │   │   └── evaluation.py
│   │   └── migrations/            # Alembic migration scripts
│   ├── cache/                     # Redis Caching Layer
│   │   ├── __init__.py
│   │   ├── redis_client.py
│   │   └── cache_manager.py       # Semantic query cache & rate limiter helper
│   ├── evaluation/                # Continuous Evaluation & Benchmark Suite
│   │   ├── __init__.py
│   │   ├── runner.py              # CLI & programmatic eval runner
│   │   ├── metrics.py             # Faithfulness, Answer Relevancy, Precision
│   │   └── datasets/              # Evaluation benchmark datasets (JSONL)
│   │       └── gold_benchmark.jsonl
│   └── schemas/                   # Pydantic Request/Response DTOs
│       ├── __init__.py
│       ├── chat.py
│       ├── documents.py
│       ├── auth.py
│       └── eval.py
├── tests/                         # Comprehensive Automated Test Suite
│   ├── conftest.py                # Pytest fixtures, mock LLMs & DB
│   ├── unit/                      # Fast unit tests
│   │   ├── test_guardrails.py
│   │   ├── test_chunking.py
│   │   ├── test_prompt_manager.py
│   │   └── test_workflow_nodes.py
│   ├── integration/               # Integration tests (mocked I/O)
│   │   ├── test_api_chat.py
│   │   ├── test_api_documents.py
│   │   └── test_rag_pipeline.py
│   ├── security/                  # Security & penetration tests
│   │   ├── test_prompt_injection.py
│   │   └── test_auth_rbac.py
│   └── eval/                      # Evaluation regression tests
│       └── test_rag_quality.py
├── chatbot_ui/                    # Modern React / Vite / Tailwind UI
│   ├── src/
│   │   ├── components/            # ChatWindow, MessageItem, CitationCard, Uploader
│   │   ├── api/                   # Axios client for backend API
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml             # Full local stack: app + postgres + redis
├── Dockerfile                     # Multi-stage security-hardened Docker build
├── pyproject.toml                 # Modern dependencies & tool configuration
├── PROJECT_AUDIT.md               # Approved technical audit & roadmap
├── ARCHITECTURE.md               # This document
└── README.md                      # Comprehensive production documentation
```

---

## 5. Security & Compliance Architecture

| Area | Threat Model | Mitigation Strategy | Implementation File |
|---|---|---|---|
| **API Auth** | Unauthorized access, token forgery | JWT with RS256 / HS256, bcrypt password hashing, token expiration | `src/core/security.py` |
| **RBAC** | Privilege escalation | Role annotations (`admin`, `user`) checked in dependency injection | `src/api/dependencies.py` |
| **Rate Limiting** | DoS, brute force, LLM wallet exhaustion | Token bucket rate limiting backed by Redis; 30 req/min per IP | `src/cache/cache_manager.py` |
| **Webhooks** | Spoofed WhatsApp messages | Cryptographic HMAC-SHA256 signature verification | `src/api/v1/whatsapp.py` |
| **Vector Injection** | Poisoned document chunks | Content sanitization on ingestion; chunk hash deduplication | `src/rag/loaders/` |
| **Prompt Injection** | System prompt override, jailbreaking | Regex pattern checks + semantic distance guardrails | `src/guardrails/input_guard.py` |
| **Hallucination** | Fabricated facts presented to user | Evaluator node grounding validation + citation verification | `src/workflow/nodes/evaluator_node.py` |
| **Secrets Management**| Leaked API keys in repo or docker | `pydantic-settings` reading from `.env` or container secrets | `src/core/config.py` |

---

## 6. Verification and Acceptance Criteria

1. **Bug Resolution**: Elimination of all hardcoded Windows paths, singleton re-init errors, and import-time execution side-effects.
2. **Unified API**: All endpoints accessible under `/api/v1` with automated Swagger/OpenAPI docs at `/docs`.
3. **RAG Precision**: Vector retrieval returns top-K results, reranked by cross-encoder, with verified citations.
4. **Resilient Agents**: LangGraph state machine handles query reformulation and retries up to 3 times before graceful fallback.
5. **Quality Gate**: Test suite passes with >85% code coverage; RAG evaluation benchmark achieves >0.80 Faithfulness and >0.80 Relevancy.
6. **Containerization**: Single command `docker compose up --build` launches the complete stack (FastAPI, PostgreSQL, Redis) with health checks passing.
