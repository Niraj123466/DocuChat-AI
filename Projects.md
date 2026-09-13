**Projects :** 

## **🔹 DocuChat-AI – Enterprise Multi-Tenant RAG & Autonomous Agent Platform**

## **(Production SaaS / Platform)**

**Tech Stack:** Python (FastAPI, SQLAlchemy, Pydantic v2), LangGraph, LangChain, Pinecone, Google Gemini, Cross-Encoder Reranking, React.js, Redis, Docker, OpenTelemetry, Prometheus, Twilio WhatsApp API

**Year:** 2025

**GitHub:** [https://github.com/Niraj123466/DocuChat-AI](https://github.com/Niraj123466/DocuChat-AI)

### **Problem**

Most generative AI document assistants suffer from critical enterprise bottlenecks: lack of tenant isolation leading to severe data leakage risks, unverified LLM hallucinations, poor retrieval precision when searching massive documents, and absent production observability and guardrails.

### **Solution**

Built an enterprise-grade, multi-tenant Retrieval-Augmented Generation (RAG) and autonomous agent platform. It orchestrates a cyclic multi-agent LangGraph workflow, enforces strict zero-trust tenant data isolation at both the database and vector namespace layers, uses cross-encoder reranking for pinpoint context retrieval, validates responses with bidirectional guardrails, and provides verifiable page-level citations.

### **Key Details & Architecture**

* **Autonomous Multi-Agent LangGraph State Machine:** Orchestrated a cyclic state graph consisting of a **Query Agent** (query decomposition & rewriting), a **Retriever Agent** (hybrid vector search + cross-encoder reranking), and an **Evaluator Agent** (answer relevancy & hallucination detection with automated self-correction loops).
* **Zero-Trust Multi-Tenant Data Isolation:** Enforced strict cryptographic JWT-based authorization where every database record, conversation, document, and vector query is dynamically scoped to the validated tenant token. Pinecone vector indices are strictly partitioned via namespaces (`user_{user_id}` and `kb_{kb_id}`) ensuring absolute mathematical isolation with zero cross-tenant bleed.
* **Hybrid Retrieval & Cross-Encoder Reranking:** Combined dense vector embeddings with BM25 keyword matching, passed through a secondary Cross-Encoder (FlashRank / sentence-transformers) to score and prioritize top-k chunks, drastically increasing Mean Reciprocal Rank (MRR) and NDCG.
* **Production Guardrails & Citation System:** Implemented bidirectional guardrails for prompt-injection defense, automated PII scrubbing, and output safety checks. Responses feature an interactive citation engine mapping AI assertions directly to source document pages and snippets.
* **Enterprise Observability & Resiliency:** Integrated OpenTelemetry distributed tracing spans, Prometheus metrics collection, token-bucket rate limiting, and dual-layer caching (Redis + thread-safe in-memory cache) with graceful degradation.
* **Omnichannel Access & SaaS Dashboard:** Built a sleek dark-glassmorphism React interface featuring conversation history, drag-and-drop file ingestion, a slide-out citation drawer, and `Cmd+K` command palette, alongside a Twilio WhatsApp webhook integration for mobile messaging.

### **Your Role & Contributions**

* Designed and built the complete backend architecture using **FastAPI**, **async SQLAlchemy ORM**, and **Pydantic v2** validation.
* Developed the **LangGraph multi-agent orchestration engine** with feedback loops, evaluation scoring, and automated retry mechanisms.
* Architected the **multi-tenant authorization system** across SQLite/PostgreSQL and Pinecone vector namespaces, preventing IDOR and unauthorized data exposure.
* Implemented the **cross-encoder reranking**, **guardrails pipeline**, and **citation extraction algorithms**.
* Built the modern **React.js dashboard** with dark glassmorphism styling, context-driven auth, and streaming responses via Server-Sent Events (SSE).
* Authored **18 comprehensive automated test suites** (unit, integration, multi-tenant security isolation) and configured **GitHub Actions CI/CD** with multi-stage Docker builds.

### **Impact**

* Achieved **85%+ RAG Faithfulness and Answer Relevancy** benchmarked against gold evaluation datasets.
* Guaranteed **100% data isolation** across tenants, validated under rigorous adversarial penetration tests.
* Delivered **sub-500ms Time-To-First-Token (TTFT)** streaming latency with multi-tier caching and optimized retrieval pipelines.

---

## **🔹 AI-Powered Resume Screening Assistant** 

## **(SaaS)**

**Tech Stack:** React.js, Node.js, Python (NLP, BERT), Firebase, Razorpay

**Year:** 2024

Github : [https://github.com/Niraj123466/AI-Powered-Resume-Screening](https://github.com/Niraj123466/AI-Powered-Resume-Screening)

### **What it does**

A SaaS platform that helps recruiters automatically screen resumes by comparing them against job descriptions using semantic understanding instead of simple keyword matching.

### **Key Details**

* Accepts resumes and job descriptions as input and computes **semantic similarity** using a **BERT-based NLP model**.

* Evaluates how well a candidate matches role requirements beyond keyword overlap.

* Includes an **on-demand payment flow** using Razorpay for recruiter access.

### **Your Role & Contributions**

* Built a **scalable Node.js backend** capable of handling multiple concurrent resume evaluations.

* Integrated **Firebase** for authentication and database management.

* Implemented **semantic similarity scoring** using Python NLP libraries and BERT.

* Developed a clean **React.js frontend** for uploading resumes and viewing match scores.

### **Impact**

* Achieved **3rd place at Hacksprints 6.0** among 50+ teams, validating both technical depth and real-world usefulness.

---

## **🔹 Anonymous Messaging Platform**

**Tech Stack:** Next.js, NextAuth, Tailwind CSS

**Year:** 2024

**Link:** [https://anonymous-messages-kappa.vercel.app/sign-in](https://anonymous-messages-kappa.vercel.app/sign-in)

**GitHub:** [https://github.com/Niraj123466/Anonymous-messages](https://github.com/Niraj123466/Anonymous-messages)

### **What it does**

A secure, real-time anonymous messaging platform where users can communicate without revealing their identity.

### **Key Details**

* Supports **role-based access control** to manage who can send or respond to messages.

* Integrates **ChatGPT API** for AI-assisted replies and message suggestions.

### **Your Role & Contributions**

* Implemented authentication using **NextAuth**, ensuring anonymity while enabling role verification.

* Integrated **AI-generated reply assistance** using the ChatGPT API.

* Optimized frontend performance and responsiveness using **Tailwind CSS**.

### **Impact**

* Delivered a fast, mobile-friendly messaging experience with privacy-first design.

---

## **🔹 Google Drive MCP Server – AI Knowledge Retrieval System**

**Tech Stack:** Python, FastMCP, Model Context Protocol (MCP), Google Drive API, Gemini Embeddings, Pinecone

**Year:** 2024

Github [: https://github.com/Niraj123466/gdrivemcp](https://github.com/Niraj123466/gdrivemcp)

### **Problem**

Large Google Drives become difficult to search, and LLMs cannot access private user data securely or efficiently.

### **Solution**

Built a **Model Context Protocol (MCP) server** that allows AI assistants (e.g., Claude) to securely and intelligently query a user’s private Google Drive.

### **Key Features**

* Connects AI assistants to Google Drive using **MCP**.

* Indexes folders and files into **Pinecone** using **Gemini embeddings**.

* Implements a **two-stage retrieval pipeline**:

  1. Identify relevant folders

  2. Perform file-level semantic search within those folders

### **Your Role & Contributions**

* Designed the **end-to-end architecture** for secure AI access to private data.

* Implemented efficient semantic retrieval to reduce cost and improve accuracy.

* Enabled natural language queries like *“find my machine learning notes”* to return precise results.

### **Impact**

* Transformed Google Drive into an **AI-queryable personal knowledge base** with improved accuracy, lower retrieval cost, and strong privacy guarantees.

