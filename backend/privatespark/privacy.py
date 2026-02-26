import json
import shutil
import zipfile
from pathlib import Path

from .config import DATA_DIR, DB_PATH, EXPORTS_DIR, UPLOADS_DIR
from .db import db_cursor


def export_all() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPORTS_DIR / "privatespark-export.zip"

    snapshot = {}
    with db_cursor() as (_, cur):
        for table in ["projects", "chats", "messages", "files", "capsules"]:
            rows = cur.execute(f"SELECT * FROM {table}").fetchall()
            snapshot[table] = [dict(r) for r in rows]

    json_path = EXPORTS_DIR / "export.json"
    json_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, arcname="privatespark.db")
        if json_path.exists():
            zf.write(json_path, arcname="export.json")
        if UPLOADS_DIR.exists():
            for file in UPLOADS_DIR.rglob("*"):
                if file.is_file():
                    zf.write(file, arcname=str(Path("uploads") / file.name))

    return out_path


def wipe_all() -> None:
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
