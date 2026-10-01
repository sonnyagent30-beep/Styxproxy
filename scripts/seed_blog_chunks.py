"""Initial backfill: chunk all published blog posts for Charon RAG.

Theme C — Charon's knowledge base is currently loaded at startup from
the posts table directly. Splitting each post into ~500-word chunks
with their headings gives Charon cleaner context windows and faster
top_k retrieval.

Approach: simple paragraph-based chunking with a heading recovery pass.
Each paragraph becomes a chunk; if a paragraph is > 500 words, it's
split on sentence boundaries.

We skip embeddings for the initial backfill (embedding is BYTEA in the
schema, NULL by default). The charon_blog_chunks script will populate
embeddings later when the embedding model is wired.

Run once after migration 018:
  /opt/styxproxy/backend/venv/bin/python3 /opt/styxproxy/backend/scripts/seed_blog_chunks.py

Idempotent: uses ON CONFLICT (post_id, chunk_index) DO UPDATE so re-runs
are safe. Skips posts that already have ≥1 chunk (use --force to overwrite).
"""

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/opt/styxproxy/backend")

_env_path = "/opt/styxproxy/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import CharonBlogChunk, Post  # noqa: E402

TARGET_WORDS_PER_CHUNK = 500
MAX_WORDS_PER_CHUNK = 800


def chunk_text(content: str) -> list[tuple[str, str]]:
    """Split post content into (heading, content) chunks.

    Heading is recovered from the most recent markdown header before
    the chunk content. If no header is present, heading is None.
    """
    # Walk through content, tracking current heading
    current_heading = None
    chunks = []
    current_paragraph = []

    def flush_paragraph(heading: str | None, words: list[str]) -> None:
        if not words:
            return
        text = " ".join(words).strip()
        if text:
            chunks.append((heading, text))

    paragraphs = re.split(r"\n\s*\n", content)
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Detect header
        m = re.match(r"^(#{1,6})\s+(.+)$", para)
        if m:
            current_heading = m.group(2).strip()
            # Flush any pending paragraph
            flush_paragraph(current_heading, current_paragraph)
            current_paragraph = []
            continue

        words = para.split()
        if len(current_paragraph) + len(words) > MAX_WORDS_PER_CHUNK:
            # Flush current, then split this paragraph
            flush_paragraph(current_heading, current_paragraph)
            current_paragraph = []
            for word in words:
                current_paragraph.append(word)
                if len(current_paragraph) >= TARGET_WORDS_PER_CHUNK:
                    flush_paragraph(current_heading, current_paragraph)
                    current_paragraph = []
        else:
            current_paragraph.extend(words)

    # Flush remainder
    flush_paragraph(current_heading, current_paragraph)

    return chunks


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-chunk even if post has chunks")
    parser.add_argument("--dry-run", action="store_true", help="Don't write, just count")
    args = parser.parse_args()

    async with async_session() as session:
        # Fetch all published posts
        stmt = select(Post).where(Post.status == "published")
        posts = (await session.execute(stmt)).scalars().all()

        total_chunks = 0
        for post in posts:
            # Check existing chunks for this post
            existing_stmt = select(CharonBlogChunk).where(CharonBlogChunk.post_id == post.id)
            existing = (await session.execute(existing_stmt)).scalars().all()
            if existing and not args.force:
                print(f"  skip {post.slug} — already has {len(existing)} chunks")
                continue

            chunks = chunk_text(post.content or "")
            if not chunks:
                print(f"  skip {post.slug} — empty content")
                continue

            if args.dry_run:
                print(f"  would insert {len(chunks)} chunks for {post.slug}")
                total_chunks += len(chunks)
                continue

            # Delete existing chunks if --force
            if existing and args.force:
                for chunk in existing:
                    await session.delete(chunk)
                await session.flush()

            for index, (heading, content) in enumerate(chunks):
                word_count = len(content.split())
                stmt = pg_insert(CharonBlogChunk).values(
                    post_id=post.id,
                    chunk_index=index,
                    heading=heading,
                    content=content,
                    word_count=word_count,
                ).on_conflict_do_update(
                    index_elements=["post_id", "chunk_index"],
                    set_={
                        "heading": heading,
                        "content": content,
                        "word_count": word_count,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )
                await session.execute(stmt)
            total_chunks += len(chunks)
            print(f"  backfilled {len(chunks)} chunks for {post.slug}")

        await session.commit()

    print(f"Done: {total_chunks} chunks total ({'dry-run' if args.dry_run else 'committed'})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
