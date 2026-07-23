"""Lightweight in-process RAG over Charon's knowledge base.

We chunk Markdown files into paragraphs, score them against the user's
message with a simple bag-of-words overlap, and return the top-k
relevant chunks for context injection.

This is intentionally simple — TF-IDF style, no embeddings, no
external vector DB. We run on Railway, where every dependency is
a liability, and the corpus is small (~5 files at launch).

When you migrate to n8n, swap this for whatever RAG node you wire
up there.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parents[3] / "data" / "charon" / "knowledge"
LEARNED_DIR = Path(__file__).parents[3] / "data" / "charon" / "learned"
# Canonical Scenarios corpus lives in the repo root (90+ markdown files).
# Loading these into RAG keeps Charon grounded in our agreed customer journeys.
SCENARIOS_DIR = Path("/root/styxproxy/scenarios")

STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "you", "i", "me", "my", "we",
    "and", "or", "of", "in", "to", "for", "can", "your", "you", "that",
    "this", "it", "on", "with", "as", "be", "by", "from", "have", "has",
    "had", "but", "if", "or", "so", "not", "what", "which", "how", "when",
    "where", "why", "who", "do", "does", "did", "would", "could", "should",
    "will", "shall", "may", "might", "must", "ought", "to",
}


@dataclass
class Chunk:
    source: str  # filename (relative to knowledge dir)
    heading: str
    content: str


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", " ", text.lower())
    tokens = [t for t in cleaned.split() if t and t not in STOPWORDS and len(t) > 1]
    return tokens


def _chunks_for_file(path: Path, source_label: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    body = path.read_text()
    current_heading = ""
    buffer: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.startswith("# "):
            # flush
            if buffer:
                chunks.append(Chunk(source=source_label, heading=current_heading or "intro", content="\n".join(buffer).strip()))
                buffer = []
            current_heading = line[2:].strip()
            continue
        if line.startswith("## "):
            if buffer:
                chunks.append(Chunk(source=source_label, heading=current_heading or "section", content="\n".join(buffer).strip()))
                buffer = []
            current_heading = line[3:].strip()
            continue
        if not line.strip():
            # paragraph break — flush paragraph
            if buffer:
                text = "\n".join(buffer).strip()
                if len(text) > 30:  # skip 1-line noise
                    chunks.append(Chunk(source=source_label, heading=current_heading or "section", content=text))
                buffer = []
            continue
        buffer.append(line)
    if buffer:
        text = "\n".join(buffer).strip()
        if len(text) > 30:
            chunks.append(Chunk(source=source_label, heading=current_heading or "section", content=text))
    return chunks


def _all_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    # Static knowledge + admin-edited learned files take priority.
    for d in (KNOWLEDGE_DIR, LEARNED_DIR):
        if not d.exists():
            continue
        for path in sorted(d.rglob("*.md")):
            label = str(path.relative_to(d.parent))
            chunks.extend(_chunks_for_file(path, label))
    # Add the canonical Scenarios corpus so the RAG is grounded in our
    # agreed customer journeys (first-time order, refund, recovery, etc.).
    if SCENARIOS_DIR.exists():
        for path in sorted(SCENARIOS_DIR.rglob("*.md")):
            label = f"scenarios/{path.name}"
            chunks.extend(_chunks_for_file(path, label))
    return chunks


_CACHE: list[Chunk] | None = None


def _chunks_cached() -> list[Chunk]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _all_chunks()
        logger.info("Indexed %d knowledge chunks", len(_CACHE))
    return _CACHE


def invalidate_cache() -> None:
    """Drop the in-process index cache — call when files change."""
    global _CACHE
    _CACHE = None


def search(query: str, top_k: int = 4) -> list[Chunk]:
    """Return top-k chunks ranked by token overlap with the query."""
    if not query.strip():
        return []
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    q_set = set(q_tokens)
    scored: list[tuple[float, Chunk]] = []
    for chunk in _chunks_cached():
        text = f"{chunk.heading}\n{chunk.content}"
        t_tokens = _tokenize(text)
        if not t_tokens:
            continue
        t_set = set(t_tokens)
        overlap = len(q_set & t_set)
        # boost when tokens appear in heading
        heading_set = set(_tokenize(chunk.heading))
        heading_overlap = len(q_set & heading_set)
        score = overlap + (heading_overlap * 2)
        # tiny bonus for length normalisation so long chunks don't always win
        score = score / (1 + len(t_tokens) / 200)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def format_context(chunks: Iterable[Chunk]) -> str:
    parts = []
    for chunk in chunks:
        parts.append(f"[source: {chunk.source} / heading: {chunk.heading}]\n{chunk.content}\n")
    return "\n---\n".join(parts)
