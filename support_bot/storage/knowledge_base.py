"""Knowledge base loader: chunks markdown files and provides semantic search via ChromaDB."""

import os
import re
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

_KB_DIR = Path(__file__).parent.parent.parent / "knowledge_base"
_CHROMA_DIR = Path(__file__).parent.parent.parent / "data" / "chroma"
_COLLECTION_NAME = "support_kb"


def _chunk_markdown(path: Path) -> list[dict]:
    """Split markdown into chunks by ## headings. Returns dicts with source/heading/content."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^## ", text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if body:
            chunks.append({"source": path.name, "heading": heading, "content": body})
    return chunks


def _load_all_chunks() -> list[dict]:
    chunks = []
    for md_file in sorted(_KB_DIR.glob("*.md")):
        chunks.extend(_chunk_markdown(md_file))
    return chunks


# --- ChromaDB singleton ---
_collection = None


def get_collection():
    global _collection
    if _collection is not None:
        return _collection

    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    ef = GoogleGenerativeAiEmbeddingFunction(api_key=os.environ["GOOGLE_API_KEY"])
    col = client.get_or_create_collection(name=_COLLECTION_NAME, embedding_function=ef)

    # Ingest on first run (empty collection)
    if col.count() == 0:
        chunks = _load_all_chunks()
        col.add(
            documents=[c["content"] for c in chunks],
            metadatas=[{"source": c["source"], "heading": c["heading"]} for c in chunks],
            ids=[f"{c['source']}::{c['heading']}" for c in chunks],
        )

    _collection = col
    return _collection


def search_chroma(query: str, top_k: int = 3) -> list[dict]:
    """Return top_k semantically relevant KB chunks as dicts with source/heading/content."""
    col = get_collection()
    results = col.query(query_texts=[query], n_results=top_k, include=["documents", "metadatas"])
    hits = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        hits.append({"source": meta["source"], "heading": meta["heading"], "content": doc})
    return hits
