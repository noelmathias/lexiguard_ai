# ⚖️ LexAI — Agentic Legal Intelligence System

> **Production-grade AI Legal Intelligence Platform powered by Multi-Agent AI, Hybrid RAG, and Local LLM Inference.**

---

## 🚀 Overview

LexAI is an end-to-end AI-powered Legal Intelligence Platform designed to provide legal guidance, contract analysis, risk assessment, document generation, and legal reasoning using a multi-agent architecture. 

Unlike traditional chatbots that rely on a single prompt-response workflow, LexAI combines decentralized agent orchestration, hybrid information retrieval, and local inference to build a robust, secure legal assistant.

### Key Architectural Pillars
*   **Multi-Agent Orchestration:** Task-specific agents collaborating to unpack complex legal queries.
*   **Hybrid Retrieval-Augmented Generation (RAG):** Merging dense semantic search with sparse keyword matching.
*   **Local LLM Inference:** Powered via Ollama for extreme data privacy and zero API dependency costs.
*   **Contract Intelligence Pipelines:** Extracting and assessing risk profiles directly from legal documents.
*   **Legal Risk Scoring:** Algorithmic confidence and threat-level assessments.

The system is engineered with a production-ready decoupled architecture using **FastAPI** for the backend and **React.js** for the user interface.

---

## ✨ Key Features

### 🤖 Multi-Agent Legal Reasoning
*   **Intent Classification:** Dynamically routes user queries to the correct specialized domain workflow.
*   **Entity Extraction:** Automatically parses critical metadata like dates, parties, jurisdictions, and financial obligations.
*   **Query Rewriting:** Optimizes raw user language into high-yield search queries for vector and keyword engines.
*   **Legal Reasoning & Guidance:** Combines multi-agent insights to formulate structured legal guidance.

### 📚 Hybrid RAG Pipeline
*   **FAISS Dense Vector Search:** Captures contextual and semantic meaning using sentence transformers.
*   **BM25 Sparse Keyword Retrieval:** Ensures precision matching for exact legal terminology, citation numbers, and statutes.
*   **Reciprocal Rank Fusion (RRF):** Blends vector and keyword results algorithmically for optimized context ranking.
*   **Context Re-ranking:** Pinpoints and surfaces the most critical legal clauses to minimize prompt noise.

### 📄 Contract Intelligence
*   **Contract Analysis:** Upload complex legal documents for instantaneous breakdowns.
*   **Clause Extraction:** Automatically isolates individual provisions (e.g., Indemnification, Termination).
*   **Risk Classification:** Categorizes identified clause vulnerabilities into clear high, medium, and low tiers.
*   **Contract Comparison:** Side-by-side analysis mapping clause variations, missing protections, and liability shifts.

### 📝 Legal Document Generation
Automated, template-driven generation of formal, structured legal drafts utilizing AI reasoning workflows:
*   FIR Drafts
*   Complaint Letters
*   Legal Notices
*   Formal Legal Documents

### 🛡️ AI Safety & Reliability
*   **Guardrail Enforcement:** Strict operational parameters to prevent toxic or out-of-bounds agent behavior.
*   **Confidence & Risk Scoring:** Real-time mathematical scores calculating data reliability and underlying risk profiles.
*   **Structured Response Validation:** Enforces strict output data shapes using Pydantic.
*   **Hallucination Mitigation:** Grounding mechanism requiring explicit source verification before generating answers.

---

## 🏗️ System Architecture

```text
       User Query
           │
           ▼
 ┌───────────────────────────────────┐
 │       Hybrid Retrieval Layer      │
 │    (FAISS + BM25 + RRF Fusion)    │
 └─────────────────┬─────────────────┘
                   │
                   ▼
 ┌───────────────────────────────────┐
 │       Multi-Agent Pipeline        │
 │  ├─ Intent Classification         │
 │  ├─ Entity Extraction             │
 │  ├─ Query Rewriting               │
 │  └─ Legal Reasoning               │
 └─────────────────┬─────────────────┘
                   │
                   ▼
 ┌───────────────────────────────────┐
 │     Risk & Confidence Scoring     │
 └─────────────────┬─────────────────┘
                   │
                   ▼
       Structured Legal Response

## 🛠️ Tech Stack

| Layer | Component | Technologies Used |
| :--- | :--- | :--- |
| **Frontend** | Framework & Build Tool | React.js, Vite |
| **Frontend** | Language & Styling | JavaScript, CSS3 |
| **Backend** | API Framework | FastAPI (Python) |
| **Backend** | Data Validation | Pydantic |
| **AI & Retrieval** | Local LLM Engine | Ollama (`Qwen2.5`) |
| **AI & Retrieval** | Vector Database | FAISS |
| **AI & Retrieval** | Keyword Matcher | BM25 |
| **AI & Retrieval** | Embeddings | Sentence Transformers |
| **Deployment & Dev** | Hosting & Proxy | Vercel (Frontend), ngrok (Secure Tunneling) |
| **Deployment & Dev** | Version Control | GitHub |
