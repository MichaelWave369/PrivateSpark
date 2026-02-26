from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader


TEXT_EXTENSIONS = {".txt", ".md", ".csv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def extract_text(path: Path, suffix: str) -> str:
    suffix = suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if suffix == ".docx":
        doc = Document(path)
        return "\n".join(par.text for par in doc.paragraphs).strip()

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".csv":
        df = pd.read_csv(path)
        return df.to_csv(index=False)

    if suffix in IMAGE_EXTENSIONS:
        return f"Image file: {path.name} (metadata-only ingest)"

    return ""
