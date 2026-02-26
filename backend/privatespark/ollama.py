import json
from collections.abc import Generator

import requests

from .config import OLLAMA_URL

TIMEOUT = 10


def status() -> bool:
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return res.ok
    except requests.RequestException:
        return False


def tags() -> tuple[list[dict], str | None]:
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=TIMEOUT)
        res.raise_for_status()
        data = res.json()
        return data.get("models", []), None
    except requests.RequestException:
        return [], "Ollama is not running. Install/start Ollama at http://localhost:11434 and retry."


def pull(model: str) -> Generator[dict, None, None]:
    try:
        with requests.post(
            f"{OLLAMA_URL}/api/pull", json={"name": model}, timeout=TIMEOUT, stream=True
        ) as res:
            res.raise_for_status()
            for line in res.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    yield {"status": line}
    except requests.RequestException as exc:
        yield {"error": f"Failed to pull model: {exc}"}


def chat_stream(model: str, messages: list[dict], options: dict | None = None):
    payload = {"model": model, "messages": messages, "stream": True, "options": options or {}}
    with requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=TIMEOUT, stream=True) as res:
        res.raise_for_status()
        for line in res.iter_lines(decode_unicode=True):
            if not line:
                continue
            yield json.loads(line)


def embed(texts: list[str], model: str) -> list[list[float]] | None:
    for endpoint, payload_fn in [
        ("/api/embed", lambda t: {"model": model, "input": t}),
        ("/api/embeddings", lambda t: {"model": model, "prompt": t[0] if t else ""}),
    ]:
        try:
            res = requests.post(f"{OLLAMA_URL}{endpoint}", json=payload_fn(texts), timeout=TIMEOUT)
            if not res.ok:
                continue
            data = res.json()
            if "embeddings" in data:
                return data["embeddings"]
            if "embedding" in data:
                return [data["embedding"]]
        except requests.RequestException:
            continue
    return None
