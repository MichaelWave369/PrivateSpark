# PrivateSpark v0.2 Core

PrivateSpark is a local-first AI workspace with a beginner-friendly noir UI.

## Highlights
- FastAPI backend with local SQLite persistence.
- Ollama integration for model listing, pulls, chat streaming, and optional embeddings.
- File ingest (PDF/TXT/MD/CSV/DOCX + image metadata) into searchable Capsules.
- Full-text search with optional embedding rerank.
- Privacy tools: local export zip + wipe-all reset.
- Graceful offline behavior when Ollama is not running.

## Project structure
- `backend/privatespark`: API, DB, Ollama client, ingest/search/privacy modules
- `backend/tests`: API tests
- `web/`: app UI (served by FastAPI)

## Local run (Windows/macOS/Linux)
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn privatespark.main:app --host 0.0.0.0 --port 4173 --reload
```
Open <http://localhost:4173>

## Optional Ollama setup
```bash
ollama serve
ollama pull llama3.1:latest
ollama pull nomic-embed-text
```

## Environment
Copy `.env.example` and set overrides as needed.

## Privacy promise
PrivateSpark is local-by-default. External network use is limited to optional local Ollama at `http://localhost:11434`.
