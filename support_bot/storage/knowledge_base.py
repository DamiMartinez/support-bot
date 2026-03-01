"""Knowledge base loader: chunks markdown files and provides text search."""

import re
from dataclasses import dataclass
from pathlib import Path

_KB_DIR = Path(__file__).parent.parent.parent / "knowledge_base"


@dataclass
class KBChunk:
    source: str      # filename
    heading: str     # section heading
    content: str     # body text
    full_text: str   # heading + content for search


def _chunk_markdown(path: Path) -> list[KBChunk]:
    """Split a markdown file into chunks by ## headings."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^## ", text)
    chunks: list[KBChunk] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if body:
            chunks.append(KBChunk(
                source=path.name,
                heading=heading,
                content=body,
                full_text=f"{heading}\n{body}",
            ))
    return chunks


def load_knowledge_base(kb_dir: Path = _KB_DIR) -> list[KBChunk]:
    """Load all .md files from the knowledge base directory."""
    chunks: list[KBChunk] = []
    if not kb_dir.exists():
        return chunks
    for md_file in sorted(kb_dir.glob("*.md")):
        chunks.extend(_chunk_markdown(md_file))
    return chunks


def _score_chunk(chunk: KBChunk, query_tokens: list[str]) -> float:
    """Simple TF-style scoring: count query token hits in chunk text."""
    text_lower = chunk.full_text.lower()
    score = sum(text_lower.count(token) for token in query_tokens)
    # Boost heading matches
    heading_lower = chunk.heading.lower()
    score += sum(3 for token in query_tokens if token in heading_lower)
    return score


def search_knowledge_base_local(
    query: str,
    chunks: list[KBChunk],
    top_k: int = 3,
) -> list[KBChunk]:
    """Return up to top_k chunks most relevant to the query."""
    query_tokens = [w.lower() for w in re.split(r"\W+", query) if len(w) > 2]
    if not query_tokens:
        return chunks[:top_k]

    scored = [(chunk, _score_chunk(chunk, query_tokens)) for chunk in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, score in scored[:top_k] if score > 0]


# Module-level singleton loaded at import time
_KB_CHUNKS: list[KBChunk] = []


def get_kb_chunks() -> list[KBChunk]:
    """Return (lazily loaded) global KB chunks."""
    global _KB_CHUNKS
    if not _KB_CHUNKS:
        _KB_CHUNKS = load_knowledge_base()
    return _KB_CHUNKS
