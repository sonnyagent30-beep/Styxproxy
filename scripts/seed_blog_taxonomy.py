"""Idempotent seed script for blog taxonomy data.

Reads /root/Styxproxy/.sprint/taxonomy.json and:
- upserts categories into the `categories` table
- sets each post's tags array
- links posts to categories via the post_categories join table
- updates each post's excerpt and meta_description

Re-runnable: uses upsert (ON CONFLICT DO UPDATE) everywhere.

Run:
  /opt/styxproxy/backend/venv/bin/python3 /opt/styxproxy/backend/scripts/seed_blog_taxonomy.py [--dry-run]
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

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
from app.models import Category, Post, PostCategory  # noqa: E402

TAXONOMY_PATH = Path("/root/Styxproxy/.sprint/taxonomy.json")


async def seed_taxonomy(dry_run: bool = False) -> dict:
    if not TAXONOMY_PATH.exists():
        raise FileNotFoundError(
            f"Taxonomy file not found: {TAXONOMY_PATH}\n"
            "Run the SEO agent first to generate it."
        )

    with open(TAXONOMY_PATH) as f:
        data = json.load(f)

    categories = data.get("categories", [])
    posts_updates = data.get("posts", [])

    # taxonomy.json uses a single `category` slug per post. Older drafts of this
    # script expected a `category_slugs` list, which silently linked nothing —
    # normalise both shapes into `category_slugs` here.
    for _p in posts_updates:
        if "category_slugs" not in _p:
            _one = _p.get("category")
            _p["category_slugs"] = [_one] if _one else []


    stats = {"categories_upserted": 0, "posts_updated": 0, "links_created": 0}

    async with async_session() as session:
        # 1. Upsert categories
        for cat in categories:
            stmt = pg_insert(Category).values(
                name=cat["name"],
                slug=cat["slug"],
                description=cat.get("description"),
                color=cat.get("color"),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["slug"],
                set_={
                    "name": stmt.excluded.name,
                    "description": stmt.excluded.description,
                    "color": stmt.excluded.color,
                },
            )
            if dry_run:
                print(f"  [DRY-RUN] upsert category: {cat['slug']}")
            else:
                await session.execute(stmt)
            stats["categories_upserted"] += 1

        # Build slug -> category_id map
        slug_to_id: dict[str, str] = {}
        if not dry_run and categories:
            result = await session.execute(
                select(Category.slug, Category.id).where(
                    Category.slug.in_([c["slug"] for c in categories])
                )
            )
            for slug, cid in result.all():
                slug_to_id[slug] = cid

        # 2. Update posts (tags, excerpt, meta_description) and link categories
        for p in posts_updates:
            slug = p["slug"]

            if dry_run:
                print(f"  [DRY-RUN] update post: {slug}")
                print(f"             tags={p.get('tags')}")
                print(f"             categories={p.get('category_slugs')}")
                stats["posts_updated"] += 1
                stats["links_created"] += len(p.get("category_slugs", []))
                continue

            # Fetch the post by slug
            result = await session.execute(select(Post).where(Post.slug == slug))
            post = result.scalar_one_or_none()
            if not post:
                print(f"  [WARN] post not found: {slug}")
                continue

            # Update tags, excerpt, meta_description
            if "tags" in p:
                post.tags = p["tags"]
            if "excerpt" in p and p["excerpt"]:
                post.excerpt = p["excerpt"]
            if "meta_description" in p and p["meta_description"]:
                post.meta_description = p["meta_description"]
            stats["posts_updated"] += 1

            # Link categories
            cat_slugs = p.get("category_slugs", [])
            if cat_slugs:
                # Delete existing links
                await session.execute(
                    PostCategory.__table__.delete().where(PostCategory.post_id == post.id)
                )
                # Insert new links
                for cat_slug in cat_slugs:
                    cat_id = slug_to_id.get(cat_slug)
                    if cat_id:
                        await session.execute(
                            PostCategory.__table__.insert().values(
                                post_id=post.id, category_id=cat_id
                            )
                        )
                        stats["links_created"] += 1
                    else:
                        print(f"  [WARN] category slug not found: {cat_slug}")

        if not dry_run:
            await session.commit()

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Seed blog taxonomy from taxonomy.json")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    print(f"Reading taxonomy from {TAXONOMY_PATH}")
    stats = await seed_taxonomy(dry_run=args.dry_run)
    print("\nDone:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
