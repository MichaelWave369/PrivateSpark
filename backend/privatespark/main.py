import hashlib
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import DEFAULT_CHAT_MODEL, EMBED_MODEL, ENABLE_EMBEDDINGS, UPLOADS_DIR, ensure_dirs
from .db import db_cursor, init_db, store_embedding, upsert_fts, utcnow
from .ingest import extract_text
from .models import ChatRequest, ProjectCreate, PullRequest, WipeRequest
from .ollama import chat_stream, embed, pull, status, tags
from .privacy import export_all, wipe_all
from .search import search_capsules

app = FastAPI(title="PrivateSpark Core", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.on_event("startup")
def startup() -> None:
    ensure_dirs()
    init_db()


@app.get("/api/healthz")
def healthz():
    return {"ok": True, "version": __version__, "ollama_available": status()}


@app.get("/api/ollama/status")
def ollama_status():
    return {
        "ok": status(),
        "url": "http://localhost:11434",
        "hint": "Install Ollama and run `ollama serve` if unavailable.",
    }


@app.get("/api/models")
def models():
    model_list, message = tags()
    return {"models": model_list, "message": message}


@app.post("/api/models/pull")
def pull_model(req: PullRequest):
    return {"ok": True, "stream_url": f"/api/models/pull/stream?model={req.model}"}


@app.get("/api/models/pull/stream")
def pull_stream(model: str = Query(...)):
    def generate():
        for chunk in pull(model):
            yield sse("progress", chunk)
        yield sse("done", {"model": model})

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/projects")
def get_projects():
    with db_cursor() as (_, cur):
        rows = cur.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return {"projects": [dict(r) for r in rows]}


@app.post("/api/projects")
def create_project(req: ProjectCreate):
    with db_cursor() as (_, cur):
        cur.execute("INSERT INTO projects(name, created_at) VALUES (?, ?)", (req.name, utcnow()))
        pid = cur.lastrowid
    return {"id": pid, "name": req.name}


@app.get("/api/projects/{project_id}/capsules")
def project_capsules(project_id: int):
    with db_cursor() as (_, cur):
        rows = cur.execute(
            "SELECT id, title, text, created_at FROM capsules WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return {"capsules": [dict(r) for r in rows]}


@app.post("/api/files/upload")
async def upload_file(project_id: int = Query(...), file: UploadFile = File(...)):
    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()
    suffix = Path(file.filename).suffix.lower()
    out_path = UPLOADS_DIR / f"{digest}{suffix}"
    out_path.write_bytes(content)

    extracted = extract_text(out_path, suffix)
    title = file.filename

    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO files(project_id, filename, mime, size, sha256, stored_path, extracted_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, file.filename, file.content_type, len(content), digest, str(out_path), extracted, utcnow()),
        )
        file_id = cur.lastrowid
        cur.execute(
            "INSERT INTO capsules(project_id, file_id, title, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, file_id, title, extracted[:12000] or f"Uploaded file: {file.filename}", utcnow()),
        )
        capsule_id = cur.lastrowid

    upsert_fts(capsule_id, title, extracted)

    if ENABLE_EMBEDDINGS and extracted.strip():
        vectors = embed([extracted[:3000]], EMBED_MODEL)
        if vectors:
            store_embedding(capsule_id, EMBED_MODEL, vectors[0])

    return {"ok": True, "capsule_id": capsule_id, "summary": (extracted[:220] + "...") if len(extracted) > 220 else extracted}


@app.get("/api/search")
def search(project_id: int, q: str):
    results = search_capsules(project_id, q, EMBED_MODEL if ENABLE_EMBEDDINGS else None)
    return {"results": results}


@app.post("/api/chat")
def chat(req: ChatRequest):
    selected_model = req.model or DEFAULT_CHAT_MODEL

    with db_cursor() as (_, cur):
        cur.execute(
            "INSERT INTO chats(project_id, title, created_at) VALUES (?, ?, ?)",
            (req.project_id, "Chat Session", utcnow()),
        )
        chat_id = cur.lastrowid
        for msg in req.messages:
            cur.execute(
                "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (chat_id, msg.role, msg.content, utcnow()),
            )

    if not status():
        def friendly():
            yield sse("error", {"message": "Ollama is offline. Install Ollama, run `ollama serve`, then `ollama pull llama3.1:latest`."})
        return StreamingResponse(friendly(), media_type="text/event-stream")

    def generate():
        full = ""
        try:
            messages = [m.model_dump() for m in req.messages]
            if req.system_prompt:
                messages = [{"role": "system", "content": req.system_prompt}] + messages
            for item in chat_stream(selected_model, messages, {"temperature": req.temperature}):
                token = item.get("message", {}).get("content", "")
                done = item.get("done", False)
                if token:
                    full += token
                    yield sse("token", {"token": token})
                if done:
                    break
            with db_cursor() as (_, cur):
                cur.execute(
                    "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (chat_id, "assistant", full or "", utcnow()),
                )
            yield sse("final", {"chat_id": chat_id, "content": full})
        except Exception as exc:  # noqa: BLE001
            yield sse("error", {"message": f"Chat failed: {exc}"})

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/privacy/export")
def privacy_export():
    out_path = export_all()
    return FileResponse(path=out_path, filename=out_path.name, media_type="application/zip")


@app.post("/api/privacy/wipe")
def privacy_wipe(req: WipeRequest):
    if req.confirm_token != "WIPE_MY_DATA":
        raise HTTPException(status_code=400, detail="Invalid confirm token. Use WIPE_MY_DATA.")
    wipe_all()
    ensure_dirs()
    init_db()
    return {"ok": True}


web_dir = Path(__file__).resolve().parents[2] / "web"
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
