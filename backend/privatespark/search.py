import json

import numpy as np

from .db import db_cursor
from .ollama import embed


def cosine(a: list[float], b: list[float]) -> float:
    av = np.array(a)
    bv = np.array(b)
    denom = np.linalg.norm(av) * np.linalg.norm(bv)
    return float(np.dot(av, bv) / denom) if denom else 0.0


def search_capsules(project_id: int, query: str, embed_model: str | None = None) -> list[dict]:
    with db_cursor() as (_, cur):
        rows = cur.execute(
            """
            SELECT c.id, c.title, c.text, c.created_at
            FROM fts f
            JOIN capsules c ON c.id = f.rowid
            WHERE c.project_id = ? AND fts MATCH ?
            LIMIT 20
            """,
            (project_id, query),
        ).fetchall()

    results = [dict(row) for row in rows]

    if not results or not embed_model:
        return results

    q_vecs = embed([query], embed_model)
    if not q_vecs:
        return results
    q_vec = q_vecs[0]

    with db_cursor() as (_, cur):
        emb_rows = cur.execute(
            "SELECT capsule_id, vector_json FROM embeddings WHERE capsule_id IN (%s)"
            % ",".join("?" for _ in results),
            tuple(r["id"] for r in results),
        ).fetchall()

    emb_map = {r["capsule_id"]: json.loads(r["vector_json"]) for r in emb_rows}
    for r in results:
        vec = emb_map.get(r["id"])
        r["score"] = cosine(q_vec, vec) if vec else 0.0

    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
