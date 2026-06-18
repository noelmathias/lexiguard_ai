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
```

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


## 📂 Project Structure

```text
LEGAL_INTELLIGENCE_SYSTEM/
│
├── backend/               # FastAPI application layer (Agents, RAG, API)
├── docker/                # Isolated environment configurations & Dockerfiles
├── frontend/              # React.js UI layer (Vite-powered Dashboard)
├── venv/                  # Local Python virtual environment (Git-ignored)
│
├── .dockerignore          # Prevents heavy local builds from entering Docker context
├── .env.example           # Public environment template for local configuration
├── .gitignore             # Dictates which files Git should completely ignore
├── Makefile               # Automation shortcuts (e.g., build, run, test)
├── README.md              # Core project documentation
├── docker-compose.yml     # Local multi-container development orchestration
├── docker-compose.prod.yml# Production-hardened container infrastructure stack
├── package.json           # Root task automation and package scripts
└── package-lock.json      # Strict dependency tree lockfile
```

## 🔍 Core Functionalities

### 1. Legal Assistant
Engage with an AI legal expert. Ask complex queries and receive contextual, statutory-grounded responses driven by `Qwen2.5` and the hybrid RAG architecture.

### 2. Contract Analysis
Drop legal documents directly into the portal to review actionable insights:
* **Granular Clause-by-Clause Analysis:** Breaks down long legal text into readable, structured segments.
* **Automated Risk Classification Metrics:** Categorizes potential vulnerabilities to catch unfavorable terms early.
* **Algorithmic Confidence Scores:** Offers transparent visibility into model validation certainty.

### 3. Contract Comparison
Upload two contrasting contracts to run differential comparisons instantly, highlighting:
* Clause differences and subtle language drift.
* Risk profile variations across mirroring sections.
* Missing provisions or critical protections overlooked in recent revisions.

### 4. Document Generation
Generate professional, ready-to-file legal documentation tailored to specific contexts using robust, pre-formatted legal templates.

---

## 📈 Engineering Highlights

* **Production-Grade Multi-Agent System:** Engineered a decoupled orchestration framework that organizes AI workflows into distinct intent, extraction, and reasoning components.
* **Advanced Fusion Retrieval:** Implemented Reciprocal Rank Fusion (RRF) to seamlessly merge dense embedding spaces with exact keyword indexes, yielding high-context precision.
* **Modular FastAPI Architecture:** Built a performant, asynchronous backend pattern keeping services, routes, and logic highly isolated and maintainable.
* **Zero-Cost Local Inference:** Successfully containerized and integrated `Ollama` running `Qwen2.5` locally, removing commercial API bottlenecks while maintaining absolute contract data privacy.
* **Deterministic Safety Layers:** Programmed mathematical verification layers mapping confidence scores to prevent hallucinated outputs across sensitive document types.

## ⚙️ Local Setup

### 1. Backend & Model Engine
Navigate to the backend directory and set up your Python environment:
```bash
cd backend
pip install -r requirements.txt
```
Boot up the local FastAPI development server:

```Bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Ensure Ollama is running and download the necessary base model in a separate terminal tab:
Start the Ollama service runtime
```Bash
ollama serve
```
Pull the Qwen2.5 3B model
```bash
ollama pull qwen2.5:3b
```
### 2. Frontend Development
Open a new terminal tab and navigate to the frontend directory:
```bash
cd frontend
```
Install the necessary node modules and spin up the Vite development server:

Install project dependencies
```bash
npm install
```
Start the local development server
```bash
npm run dev
```

## 🌐 Deployment Configuration

### Current Architecture
* **Frontend UI:** Deployed on **Vercel** for fast edge distribution.
* **Backend Server:** Hosted locally and securely exposed to Vercel instances via an **ngrok tunnel**, minimizing configuration costs while testing live systems.

### 🔮 Future Production Roadmap
To transition LexAI out of development, the target infrastructure plan includes:
* **AWS EC2:** Hosting the core FastAPI application and underlying vector indexes on high-availability compute layers.
* **Docker Compose:** Multi-container orchestration separating the Web API, the vector store, and the Ollama service runtime.
* **Nginx Reverse Proxy:** Acting as an internet facing gateway handling load balancing and request routing.
* **Let's Encrypt:** Automated TLS configuration for enforcing system-wide HTTPS.

---

## 🎯 Resume Highlights

* Multi-Agent AI Architecture & Orchestration
* Hybrid Retrieval-Augmented Generation (RAG) Systems
* Production-Ready FastAPI Backend Engineering
* Local LLM Performance Optimization & Ollama Operations
* Contract Intelligence & Risk Assessment Pipelines
* Full-Stack AI Software Engineering
* AI Safety, Deterministic Guardrails, & System Reliability
* Cloud Infrastructure, Docker, & Deployment Workflows

---

## 🔮 Future Enhancements

- [ ] **Persistent Workspace Storage:** Save past chats, uploaded agreements, and drafts directly to a database.
- [ ] **User Authentication:** Enterprise-ready user access via JWT/OAuth2 mechanisms.
- [ ] **Production Cloud Infrastructure:** Transition from tunnels to automated AWS EC2 and Docker deployments.
- [ ] **Streaming Responses:** Implement Server-Sent Events (SSE) for low-latency, real-time message streaming.
- [ ] **Advanced Evaluation Framework:** Integrate objective testing platforms (like Ragas or TruLens) to mathematically track precision and factual recall.
- [ ] **Multi-Model Support:** Add fallback support for alternative open-weights models (e.g., Llama 3, Mistral).

---

## 👨‍💻 Author

**Noel Mathias** 
*Computer Science (AI & ML) Student*

* **Core Focus Areas:** Artificial Intelligence, Machine Learning, Generative/Agentic Systems, and Full-Stack AI Engineering.

---
* If you find this legal intelligence project interesting, consider starring this repository!* ⭐
