import os
from pathlib import Path


def _default_data_dir() -> Path:
    explicit = os.getenv("PRIVATESPARK_DATA_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()

    if os.getenv("PRIVATESPARK_DEV_DATA", "0") == "1":
        return Path("./data").resolve()

    home = Path.home()
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        base = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base / "PrivateSpark"

    if "darwin" in os.uname().sysname.lower():
        return home / "Library" / "Application Support" / "PrivateSpark"

    return home / ".local" / "share" / "PrivateSpark"


DATA_DIR = _default_data_dir()
UPLOADS_DIR = DATA_DIR / "uploads"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "privatespark.db"
PORT = int(os.getenv("PRIVATESPARK_PORT", "4173"))
OLLAMA_URL = os.getenv("PRIVATESPARK_OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("PRIVATESPARK_EMBED_MODEL", "nomic-embed-text")
DEFAULT_CHAT_MODEL = os.getenv("PRIVATESPARK_DEFAULT_CHAT_MODEL", "llama3.1:latest")
ENABLE_EMBEDDINGS = os.getenv("PRIVATESPARK_ENABLE_EMBEDDINGS", "1") == "1"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
