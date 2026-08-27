"""Lightweight in-process RAG over Charon's knowledge base.

Sources:
- Static knowledge files (data/charon/knowledge/)
- Learned files (data/charon/learned/)
- Scenarios corpus (/root/styxproxy/scenarios/)
- Blog posts (from the database — kept in sync via signal)

Simple bag-of-words scoring. No embeddings, no external vector DB.
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
SCENARIOS_DIR = Path("/root/styxproxy/scenarios")

STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "you", "i", "me", "my", "we",
    "and", "or", "of", "in", "to", "for", "can", "your", "that", "this",
    "it", "on", "with", "as", "be", "by", "from", "have", "has", "had",
    "but", "if", "so", "not", "what", "which", "how", "when", "where",
    "why", "who", "does", "did", "would", "could", "should", "will",
    "shall", "may", "might", "must", "ought",
}


@dataclass
class Chunk:
    source: str  # filename or "blog/{slug}"
    heading: str
    content: str
    url: str | None = None  # for blog posts, link to the article


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", " ", text.lower())
    tokens = [t for t in cleaned.split() if t and t not in STOPWORDS and len(t) > 1]
    return tokens


def _chunks_for_file(path: Path, source_label: str, url: str | None = None) -> list[Chunk]:
    chunks: list[Chunk] = []
    body = path.read_text(encoding="utf-8", errors="ignore")
    current_heading = ""
    buffer: list[str] = []
    
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.startswith("# "):
            if buffer:
                chunks.append(
                    Chunk(source=source_label, heading=current_heading or "intro",
                          content="\n".join(buffer).strip(), url=url)
                )
                buffer = []
            current_heading = line[2:].strip()
            continue
        if line.startswith("## "):
            if buffer:
                chunks.append(
                    Chunk(source=source_label, heading=current_heading or "section",
                          content="\n".join(buffer).strip(), url=url)
                )
                buffer = []
            current_heading = line[3:].strip()
            continue
        if not line.strip():
            if buffer:
                text = "\n".join(buffer).strip()
                if len(text) > 30:
                    chunks.append(
                        Chunk(source=source_label, heading=current_heading or "section",
                              content=text, url=url)
                    )
                buffer = []
            continue
        buffer.append(line)
    
    if buffer:
        text = "\n".join(buffer).strip()
        if len(text) > 30:
            chunks.append(
                Chunk(source=source_label, heading=current_heading or "section",
                      content=text, url=url)
            )
    return chunks


def _chunks_from_blog_posts() -> list[Chunk]:
    """Fetch published blog posts from the database and index them."""
    chunks: list[Chunk] = []
    try:
        import asyncio
        from app.database import async_session
        from app.models import Post, Category, PostCategory
        from sqlalchemy import select
        
        async def fetch_posts():
            async with async_session() as session:
                # Get published posts with their categories
                stmt = (
                    select(Post, Category.name)
                    .join(PostCategory, PostCategory.post_id == Post.id, isouter=True)
                    .join(Category, Category.id == PostCategory.category_id, isouter=True)
                    .where(Post.status == "published")
                    .order_by(Post.published_at.desc())
                    .limit(50)
                )
                result = await session.execute(stmt)
                return result.all()
        
        try:
            loop = asyncio.get_running_loop()
            return []
        except RuntimeError:
            rows = asyncio.run(fetch_posts())
        
        # Group by post (since join creates multiple rows for multiple categories)
        seen_posts = set()
        for post, category_name in rows:
            if post.id in seen_posts:
                continue
            seen_posts.add(post.id)
            
            source = f"blog/{post.slug}"
            url = f"https://styxproxy.com/blog/{post.slug}"
            
            # Index title + excerpt as one chunk
            title_content = f"{post.title}\n\n{post.excerpt or ''}".strip()
            if title_content and len(title_content) > 20:
                chunks.append(Chunk(
                    source=source,
                    heading=post.title,
                    content=title_content,
                    url=url,
                ))
            
            # Index full content broken into sections
            if post.content:
                current_heading = post.title
                buffer: list[str] = []
                for line in post.content.splitlines():
                    if line.startswith("#"):
                        if buffer:
                            text = "\n".join(buffer).strip()
                            if len(text) > 30:
                                chunks.append(Chunk(
                                    source=source,
                                    heading=current_heading,
                                    content=text,
                                    url=url,
                                ))
                            buffer = []
                        current_heading = line.lstrip("#").strip() or post.title
                    else:
                        buffer.append(line)
                if buffer:
                    text = "\n".join(buffer).strip()
                    if len(text) > 30:
                        chunks.append(Chunk(
                            source=source,
                            heading=current_heading,
                            content=text,
                            url=url,
                        ))
        
        logger.info("Indexed %d chunks from blog posts", len(chunks))
    except Exception as exc:
        logger.warning("Failed to index blog posts: %s", exc)
    
    return chunks


def _all_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    
    # Static knowledge + admin-edited learned files
    for d in (KNOWLEDGE_DIR, LEARNED_DIR):
        if not d.exists():
            continue
        for path in sorted(d.rglob("*.md")):
            label = str(path.relative_to(d.parent))
            chunks.extend(_chunks_for_file(path, label))
    
    # Scenarios corpus
    if SCENARIOS_DIR.exists():
        for path in sorted(SCENARIOS_DIR.rglob("*.md")):
            label = f"scenarios/{path.name}"
            chunks.extend(_chunks_for_file(path, label))
    
    # Blog posts from database
    chunks.extend(_chunks_from_blog_posts())
    
    return chunks


_CACHE: list[Chunk] | None = None


def _chunks_cached() -> list[Chunk]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _all_chunks()
        logger.info("Indexed %d knowledge chunks total", len(_CACHE))
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
        heading_set = set(_tokenize(chunk.heading))
        heading_overlap = len(q_set & heading_set)
        score = overlap + (heading_overlap * 2)
        score = score / (1 + len(t_tokens) / 200)
        if score > 0:
            scored.append((score, chunk))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def format_context(chunks: Iterable[Chunk]) -> str:
    parts = []
    for chunk in chunks:
        url_part = f" / url: {chunk.url}" if chunk.url else ""
        parts.append(f"[source: {chunk.source} / heading: {chunk.heading}{url_part}]\n{chunk.content}\n")
    return "\n---\n".join(parts)
