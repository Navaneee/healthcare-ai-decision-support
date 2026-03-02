# 🏥 AI Healthcare Decision Support Analysis System

A multi-agent medical report analysis pipeline built with CrewAI, 
RAG, FastAPI, and Streamlit. Automates patient report analysis 
using 4 specialized AI agents grounded in real WHO and NIH 
medical guidelines.

## 🎯 Project Overview

This system automates the process of analyzing patient medical 
reports using multiple AI agents working in sequence. A human 
reviewer validates all AI outputs before finalization — 
implementing Human-in-the-Loop (HITL) design.

## 🏗️ Architecture
```
Patient Report Submitted
        ↓
Agent 1 — Report Analyzer (extracts health indicators)
        ↓
Agent 2 — Guideline Retriever (RAG search on WHO/NIH docs)
        ↓
Agent 3 — Risk Explainer (assesses risk levels)
        ↓
Agent 4 — Safety Validator (identifies safety concerns)
        ↓
Human Reviewer → Approve / Reject
        ↓
Final Output Stored
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Multi-Agent Framework | CrewAI |
| LLM | Ollama Mistral (local) |
| Embeddings | nomic-embed-text (Ollama) |
| Vector Store | ChromaDB |
| Backend | FastAPI |
| Database | SQLite + SQLAlchemy |
| Frontend | Streamlit |
| Knowledge Base | WHO + NIH PDFs |

## ✨ Key Features

- **Multi-Agent Pipeline** — 4 specialized AI agents
- **RAG** — Grounded in real WHO and NIH guidelines
- **Human-in-the-Loop** — Human review before final output
- **Auto Re-trigger** — Pipeline re-runs on rejection with feedback
- **Fully Local** — No external APIs, all data stays on machine
- **Audit Trail** — Complete history of every action

## 🚀 Setup Instructions

### Prerequisites
- Python 3.11+
- Ollama installed (https://ollama.com)
- Git

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/healthcare-ai-decision-support.git
cd healthcare-ai-decision-support
```

### 2. Pull Ollama models
```bash
ollama pull mistral
ollama pull nomic-embed-text
```

### 3. Add medical guideline PDFs
Download and place PDFs in:
```
guidelines/
  ├── hypertension/
  ├── diabetes/
  └── cholesterol/
```

### 4. Run document ingestion
```bash
python ingest.py
```

### 5. Start FastAPI backend
```bash
uvicorn backend.api:app --reload --port 8000
```

### 6. Start Streamlit frontend
```bash
streamlit run app.py
```

### 7. Run CrewAI pipeline
```bash
crewai run
```

## 📁 Project Structure
```
medical_analysis/
  ├── src/medical_analysis/
  │     ├── config/
  │     │     ├── agents.yaml
  │     │     └── tasks.yaml
  │     ├── crew.py
  │     ├── main.py
  │     └── custom_tool.py
  ├── backend/
  │     ├── api.py
  │     ├── database.py
  │     └── alerts.py
  ├── guidelines/
  ├── chroma_db/
  ├── app.py
  ├── ingest.py
  └── pyproject.toml
```

## 🔄 Human Review Workflow

1. Pipeline completes → reviewer alerted
2. Reviewer opens Streamlit review page
3. Reviews all 4 agent outputs
4. Approves or rejects with notes
5. Rejection triggers automatic re-run with feedback

## 👤 Author
Your Name