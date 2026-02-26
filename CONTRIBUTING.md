# Contributing to PrivateSpark

## Local development
1. `cd backend`
2. `python -m venv .venv`
3. Activate venv:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn privatespark.main:app --host 0.0.0.0 --port 4173 --reload`
6. Open `http://localhost:4173`

## Guidelines
- Keep features local-first by default.
- Do not add external cloud calls unless clearly opt-in.
- Add tests for API changes under `backend/tests`.
