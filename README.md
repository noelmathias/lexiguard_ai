⚖️ LexAI — Agentic Legal Intelligence System

Production-grade AI Legal Intelligence Platform powered by Multi-Agent AI, Hybrid RAG, and Local LLM Inference.











🚀 Overview

LexAI is an end-to-end AI-powered Legal Intelligence Platform designed to provide legal guidance, contract analysis, risk assessment, document generation, and legal reasoning using a multi-agent architecture.

Unlike traditional chatbots that rely on a single prompt-response workflow, LexAI combines:



Multi-Agent Orchestration

Hybrid Retrieval-Augmented Generation (RAG)

Local LLM Inference via Ollama

Contract Intelligence Pipelines

Legal Risk Scoring

AI-Powered Document Generation

The system is designed with production-style architecture using FastAPI, React, and modular AI pipelines.

✨ Key Features

🤖 Multi-Agent Legal Reasoning

Intent Classification

Entity Extraction

Query Rewriting

Legal Reasoning & Guidance Generation

📚 Hybrid RAG Pipeline

FAISS Dense Vector Search

BM25 Sparse Keyword Retrieval

Reciprocal Rank Fusion (RRF)

Context Re-ranking

📄 Contract Intelligence

Contract Analysis

Clause Extraction

Risk Classification

Contract Comparison

Risk Scoring

📝 Legal Document Generation

Generate:



FIR Drafts

Complaint Letters

Legal Notices

Formal Legal Documents

🛡️ AI Safety & Reliability

Guardrail Enforcement

Confidence Scoring

Risk Scoring

Structured Response Validation

Hallucination Mitigation

🏗️ System Architecture

User Query

    │

    ▼

Hybrid Retrieval Layer

(FAISS + BM25 + RRF)

    │

    ▼

Multi-Agent Pipeline

 ├─ Intent Classification

 ├─ Entity Extraction

 ├─ Query Rewriting

 └─ Legal Reasoning

    │

    ▼

Risk & Confidence Scoring

    │

    ▼

Structured Legal Response

🛠️ Tech Stack

Frontend

React.js

Vite

JavaScript

CSS

Backend

FastAPI

Python

Pydantic

AI & Retrieval

Ollama

Qwen2.5

FAISS

BM25

Sentence Transformers

Hybrid RAG

Deployment

Vercel

ngrok

GitHub

📂 Project Structure

LEXIGUARD_AI/

│

├── backend/

│   ├── api/

│   ├── core/

│   ├── models/

│   ├── utils/

│   ├── evaluation/

│   ├── data_pipeline/

│   ├── main.py

│   └── requirements.txt

│

├── frontend/

│   ├── src/

│   ├── public/

│   ├── pages/

│   ├── components/

│   └── package.json

│

└── README.md

🔍 Core Functionalities

Legal Assistant

Ask legal questions and receive contextual responses powered by Hybrid RAG and local LLM inference.



Contract Analysis

Upload contracts and receive:



Clause Analysis

Risk Assessment

Confidence Scores

Actionable Guidance

Contract Comparison

Compare two legal documents and identify:



Clause Differences

Risk Variations

Missing Provisions

Document Generation

Generate structured legal documents using AI-powered templates and reasoning workflows.

📈 Engineering Highlights

Built a production-grade multi-agent orchestration pipeline.

Implemented Hybrid RAG using FAISS + BM25 + Reciprocal Rank Fusion.

Designed modular FastAPI architecture with reusable services.

Integrated local LLM inference using Ollama and Qwen2.5.

Implemented rule-based Risk & Confidence Scoring pipelines.

Added guardrail enforcement and hallucination mitigation mechanisms.

Developed end-to-end deployment workflow with Vercel and secure backend tunneling.

⚙️ Local Setup

Backend

cd backend



pip install -r requirements.txt



uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Ollama

ollama serve



ollama pull qwen2.5:3b

Frontend

cd frontend



npm install



npm run dev

🌐 Deployment

Frontend

Vercel

Backend

FastAPI

Ollama

ngrok tunnel

Future production deployment:



AWS EC2

Docker Compose

Nginx Reverse Proxy

HTTPS via Let's Encrypt

🎯 Resume Highlights

Multi-Agent AI Systems

Hybrid Retrieval-Augmented Generation

FastAPI Backend Engineering

Local LLM Deployment with Ollama

Contract Intelligence Systems

Full-Stack AI Engineering

AI Safety & Guardrails

Production Deployment Workflows

🔮 Future Enhancements

Persistent Workspace Storage

User Authentication

AWS EC2 Production Deployment

Dockerized Infrastructure

Streaming Responses

Advanced Evaluation Framework

Multi-Model Support

👨‍💻 Author

Noel Mathias

Computer Science (AI & ML) Student

Interested in:



Artificial Intelligence

Machine Learning

Generative AI

Agentic AI Systems

Full-Stack AI Engineering

⭐ If you found this project interesting, consider starring the repository.







i need this in README.md format to put it in github
