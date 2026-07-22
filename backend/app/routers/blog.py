"""Blog router - public and admin endpoints for blog posts."""
import re
import unicodedata
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, insert

from app.database import get_session
from app.models import Post, Category, PostCategory
from app.schemas import (
    PostCreateRequest,
    PostUpdateRequest,
    PostResponse,
    PostBriefResponse,
    PostListResponse,
    PostSubmitRequest,
    PostSubmitResponse,
    PostApproveRequest,
    PostRejectRequest,
    PostReviewResponse,
    PostPublishRequest,
    PostPublishResponse,
    PostScheduleRequest,
    PostScheduleResponse,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryResponse,
    CategoryListResponse,
)
from app.auth import admin_only, verify_admin_token

router = APIRouter(prefix="/api/blog", tags=["blog"])

# Settings
BLOG_TITLE = "Styxproxy Blog"
BLOG_DESCRIPTION = "Latest news and updates from Styxproxy"
BLOG_URL = "https://styxproxy.com"


def generate_slug(title: str) -> str:
    """Generate a URL-safe slug from a title."""
    # Normalize unicode characters
    slug = unicodedata.normalize("NFKD", title)
    # Convert to lowercase and replace spaces with hyphens
    slug = slug.lower()
    # Remove non-alphanumeric characters (keep hyphens and spaces)
    slug = re.sub(r"[^\w\s-]", "", slug)
    # Replace spaces with hyphens
    slug = re.sub(r"[\s]+", "-", slug)
    # Remove duplicate hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


async def generate_unique_slug(session: AsyncSession, title: str) -> str:
    """Generate a unique slug, appending a number if necessary."""
    base_slug = generate_slug(title)
    slug = base_slug
    
    # Check for existing slug
    counter = 1
    while True:
        stmt = select(Post).where(Post.slug == slug)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


def generate_category_slug(name: str) -> str:
    """Generate a URL-safe slug from a category name."""
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


async def get_post_categories(session: AsyncSession, post_id: UUID) -> list[dict]:
    """Get categories for a post."""
    stmt = (
        select(Category)
        .join(PostCategory, Category.id == PostCategory.category_id)
        .where(PostCategory.post_id == post_id)
    )
    result = await session.execute(stmt)
    categories = result.scalars().all()
    return [
        {"id": str(c.id), "name": c.name, "slug": c.slug, "color": c.color}
        for c in categories
    ]


async def update_post_categories(
    session: AsyncSession, post_id: UUID, category_ids: list[UUID]
) -> None:
    """Update categories for a post."""
    # Delete existing categories
    stmt = PostCategory.__table__.delete().where(PostCategory.post_id == post_id)
    await session.execute(stmt)
    
    # Add new categories
    for category_id in category_ids:
        await session.execute(
            PostCategory.__table__.insert().values(
                post_id=post_id, category_id=category_id
            )
        )


# ============== Public Endpoints ==============

@router.get("/posts", response_model=PostListResponse)
async def list_published_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    tag: Optional[str] = None,
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
):
    """List all published blog posts (public)."""
    conditions = [Post.status == "published"]
    
    if tag:
        conditions.append(Post.tags.contains([tag]))
    
    if category:
        # Join with post_categories to filter by category slug
        stmt = select(Category.id).where(Category.slug == category)
        cat_result = await session.execute(stmt)
        cat = cat_result.scalar_one_or_none()
        if cat:
            conditions.append(
                Post.id.in_(
                    select(PostCategory.post_id).where(
                        PostCategory.category_id == cat
                    )
                )
            )
    
    if featured is not None:
        conditions.append(Post.featured == featured)
    
    count_stmt = select(func.count()).select_from(Post).where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    
    offset = (page - 1) * limit
    stmt = (
        select(Post)
        .where(and_(*conditions))
        .order_by(Post.published_at.desc())
        .offset(offset)
        .limit(limit)
    )
    posts = (await session.execute(stmt)).scalars().all()
    
    return PostListResponse(
        posts=[PostBriefResponse.model_validate(p) for p in posts],
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/posts/{slug}", response_model=PostResponse)
async def get_post_by_slug(slug: str, session: AsyncSession = Depends(get_session)):
    """Get a published blog post by slug (public)."""
    stmt = select(Post).where(
        and_(Post.slug == slug, Post.status == "published")
    )
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Increment view count
    post.view_count += 1
    await session.commit()
    
    return PostResponse.model_validate(post)


@router.get("/rss.xml")
async def rss_feed(session: AsyncSession = Depends(get_session)):
    """Generate RSS 2.0 feed for published posts."""
    from fastapi.responses import Response
    
    stmt = (
        select(Post)
        .where(Post.status == "published")
        .order_by(Post.published_at.desc())
        .limit(20)
    )
    posts = (await session.execute(stmt)).scalars().all()
    
    # Build RSS XML
    items = []
    for post in posts:
        item = f"""<item>
        <title><![CDATA[{post.title}]]></title>
        <link>{BLOG_URL}/blog/{post.slug}</link>
        <guid isPermaLink="true">{BLOG_URL}/blog/{post.slug}</guid>
        <description><![CDATA[{post.excerpt or post.content[:200]}]]></description>
        <pubDate>{post.published_at.strftime('%a, %d %b %Y %H:%M:%S GMT') if post.published_at else ''}</pubDate>
        <author>{post.author}</author>
    </item>"""
        items.append(item)
    
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>{BLOG_TITLE}</title>
    <link>{BLOG_URL}</link>
    <description>{BLOG_DESCRIPTION}</description>
    <language>en-us</language>
    <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
    {"".join(items)}
</channel>
</rss>"""
    
    return Response(content=rss, media_type="application/rss+xml")


@router.get("/posts/featured", response_model=PostListResponse)
async def list_featured_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """List featured blog posts (public)."""
    conditions = [Post.status == "published", Post.featured == True]
    
    count_stmt = select(func.count()).select_from(Post).where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    
    offset = (page - 1) * limit
    stmt = (
        select(Post)
        .where(and_(*conditions))
        .order_by(Post.published_at.desc())
        .offset(offset)
        .limit(limit)
    )
    posts = (await session.execute(stmt)).scalars().all()
    
    return PostListResponse(
        posts=[PostBriefResponse.model_validate(p) for p in posts],
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


# ============== Category Endpoints ==============

@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List all categories (public)."""
    count_stmt = select(func.count()).select_from(Category)
    total = (await session.execute(count_stmt)).scalar() or 0
    
    offset = (page - 1) * limit
    stmt = (
        select(Category)
        .order_by(Category.name.asc())
        .offset(offset)
        .limit(limit)
    )
    categories = (await session.execute(stmt)).scalars().all()
    
    # Get post counts for each category
    result_categories = []
    for cat in categories:
        count_stmt = select(func.count()).select_from(PostCategory).where(
            PostCategory.category_id == cat.id
        )
        post_count = (await session.execute(count_stmt)).scalar() or 0
        result_categories.append(
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                color=cat.color,
                created_at=cat.created_at,
                updated_at=cat.updated_at,
                post_count=post_count,
            )
        )
    
    return CategoryListResponse(
        categories=result_categories,
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/categories/{slug}", response_model=CategoryResponse)
async def get_category(slug: str, session: AsyncSession = Depends(get_session)):
    """Get a category by slug (public)."""
    stmt = select(Category).where(Category.slug == slug)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    # Get post count
    count_stmt = select(func.count()).select_from(PostCategory).where(
        PostCategory.category_id == category.id
    )
    post_count = (await session.execute(count_stmt)).scalar() or 0
    
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        created_at=category.created_at,
        updated_at=category.updated_at,
        post_count=post_count,
    )


# ============== Admin Category Endpoints ==============

@router.post("/admin/categories", response_model=CategoryResponse, dependencies=[Depends(admin_only)])
async def create_category(
    request: CategoryCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new category (admin only)."""
    slug = generate_category_slug(request.name)
    
    # Check for existing slug
    stmt = select(Category).where(Category.slug == slug)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        # Append counter
        counter = 1
        while existing:
            slug = f"{generate_category_slug(request.name)}-{counter}"
            stmt = select(Category).where(Category.slug == slug)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            counter += 1
    
    category = Category(
        name=request.name,
        slug=slug,
        description=request.description,
        color=request.color,
    )
    
    session.add(category)
    await session.commit()
    await session.refresh(category)
    
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        created_at=category.created_at,
        updated_at=category.updated_at,
        post_count=0,
    )


@router.get("/admin/categories", response_model=CategoryListResponse, dependencies=[Depends(admin_only)])
async def list_all_categories(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List all categories with post counts (admin only)."""
    count_stmt = select(func.count()).select_from(Category)
    total = (await session.execute(count_stmt)).scalar() or 0
    
    offset = (page - 1) * limit
    stmt = (
        select(Category)
        .order_by(Category.name.asc())
        .offset(offset)
        .limit(limit)
    )
    categories = (await session.execute(stmt)).scalars().all()
    
    result_categories = []
    for cat in categories:
        count_stmt = select(func.count()).select_from(PostCategory).where(
            PostCategory.category_id == cat.id
        )
        post_count = (await session.execute(count_stmt)).scalar() or 0
        result_categories.append(
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                color=cat.color,
                created_at=cat.created_at,
                updated_at=cat.updated_at,
                post_count=post_count,
            )
        )
    
    return CategoryListResponse(
        categories=result_categories,
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/admin/categories/{category_id}", response_model=CategoryResponse, dependencies=[Depends(admin_only)])
async def get_category_admin(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a category by ID (admin only)."""
    stmt = select(Category).where(Category.id == category_id)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    count_stmt = select(func.count()).select_from(PostCategory).where(
        PostCategory.category_id == category.id
    )
    post_count = (await session.execute(count_stmt)).scalar() or 0
    
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        created_at=category.created_at,
        updated_at=category.updated_at,
        post_count=post_count,
    )


@router.patch("/admin/categories/{category_id}", response_model=CategoryResponse, dependencies=[Depends(admin_only)])
async def update_category(
    category_id: UUID,
    request: CategoryUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update a category (admin only)."""
    stmt = select(Category).where(Category.id == category_id)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    if request.name is not None:
        category.name = request.name
        category.slug = generate_category_slug(request.name)
    
    if request.description is not None:
        category.description = request.description
    
    if request.color is not None:
        category.color = request.color
    
    await session.commit()
    await session.refresh(category)
    
    count_stmt = select(func.count()).select_from(PostCategory).where(
        PostCategory.category_id == category.id
    )
    post_count = (await session.execute(count_stmt)).scalar() or 0
    
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        created_at=category.created_at,
        updated_at=category.updated_at,
        post_count=post_count,
    )


@router.delete("/admin/categories/{category_id}", dependencies=[Depends(admin_only)])
async def delete_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a category (admin only)."""
    stmt = select(Category).where(Category.id == category_id)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    await session.delete(category)
    await session.commit()
    
    return {"status": "deleted", "category_id": str(category_id)}


# ============== Admin Endpoints ==============

@router.post("/posts", response_model=PostResponse, dependencies=[Depends(admin_only)])
async def create_post(
    request: PostCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new blog post (admin only)."""
    # Get admin phone from request state (set by middleware)
    from fastapi import Request
    # Use a default admin for now since admin_only doesn't return phone
    admin_phone = "admin"
    slug = await generate_unique_slug(session, request.title)
    
    post = Post(
        title=request.title,
        slug=slug,
        content=request.content,
        excerpt=request.excerpt,
        cover_image_url=request.cover_image_url,
        author=admin_phone,
        status="draft",
        meta_description=request.meta_description,
        tags=request.tags,
        scheduled_at=request.scheduled_at,
        featured=request.featured,
    )
    
    session.add(post)
    await session.commit()
    await session.refresh(post)
    
    # Update categories if provided
    if request.category_ids:
        await update_post_categories(session, post.id, request.category_ids)
    
    # Get categories for response
    categories = await get_post_categories(session, post.id)
    
    response_data = PostResponse.model_validate(post)
    response_data.categories = categories
    return response_data


@router.get("/admin/posts", response_model=PostListResponse, dependencies=[Depends(admin_only)])
async def list_all_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """List all blog posts with filters (admin only)."""
    conditions = []
    
    if status_filter:
        conditions.append(Post.status == status_filter)
    
    if search:
        escaped = re.sub(r"([%_\\])", r"\\\1", search)
        conditions.append(
            (Post.title.ilike(f"%{escaped}%", escape="\\"))
            | (Post.slug.ilike(f"%{escaped}%", escape="\\"))
        )
    
    count_stmt = select(func.count()).select_from(Post)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    
    offset = (page - 1) * limit
    stmt = (
        select(Post)
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))
    posts = (await session.execute(stmt)).scalars().all()
    
    return PostListResponse(
        posts=[PostBriefResponse.model_validate(p) for p in posts],
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/admin/posts/{post_id}", response_model=PostResponse, dependencies=[Depends(admin_only)])
async def get_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a blog post by ID (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    return PostResponse.model_validate(post)


@router.patch("/admin/posts/{post_id}", response_model=PostResponse, dependencies=[Depends(admin_only)])
async def update_post(
    post_id: UUID,
    request: PostUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update a blog post (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Update fields if provided
    if request.title is not None:
        post.title = request.title
        # Regenerate slug if title changed
        if request.title != post.title:
            post.slug = await generate_unique_slug(session, request.title)
    
    if request.content is not None:
        post.content = request.content
    
    if request.excerpt is not None:
        post.excerpt = request.excerpt
    
    if request.cover_image_url is not None:
        post.cover_image_url = request.cover_image_url
    
    if request.meta_description is not None:
        post.meta_description = request.meta_description
    
    if request.tags is not None:
        post.tags = request.tags  # type: ignore
    
    if request.scheduled_at is not None:
        post.scheduled_at = request.scheduled_at
    
    if request.featured is not None:
        post.featured = request.featured
    
    await session.commit()
    await session.refresh(post)
    
    # Update categories if provided
    if request.category_ids is not None:
        await update_post_categories(session, post.id, request.category_ids)
    
    # Get categories for response
    categories = await get_post_categories(session, post.id)
    
    response_data = PostResponse.model_validate(post)
    response_data.categories = categories
    return response_data


@router.delete("/admin/posts/{post_id}", dependencies=[Depends(admin_only)])
async def delete_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a blog post (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    await session.delete(post)
    await session.commit()
    
    return {"status": "deleted", "post_id": str(post_id)}


@router.post("/admin/posts/{post_id}/submit", response_model=PostSubmitResponse, dependencies=[Depends(admin_only)])
async def submit_post(
    post_id: UUID,
    request: PostSubmitRequest,
    session: AsyncSession = Depends(get_session),
):
    """Submit a post for review (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.status not in ["draft", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit post with status '{post.status}'",
        )
    
    post.status = "pending"
    post.submitted_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(post)
    
    return PostSubmitResponse(
        post_id=post.id,
        status=post.status,
        submitted_at=post.submitted_at,
    )


@router.post("/admin/posts/{post_id}/approve", response_model=PostReviewResponse, dependencies=[Depends(admin_only)])
async def approve_post(
    post_id: UUID,
    request: PostApproveRequest,
    session: AsyncSession = Depends(get_session),
):
    """Approve a post (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve post with status '{post.status}'",
        )
    
    post.status = "approved"
    post.reviewed_by = "admin"
    post.reviewed_at = datetime.utcnow()
    post.rejection_reason = None
    
    await session.commit()
    await session.refresh(post)
    
    return PostReviewResponse(
        post_id=post.id,
        status=post.status,
        reviewed_by=post.reviewed_by,
        reviewed_at=post.reviewed_at,
    )


@router.post("/admin/posts/{post_id}/reject", response_model=PostReviewResponse, dependencies=[Depends(admin_only)])
async def reject_post(
    post_id: UUID,
    request: PostRejectRequest,
    session: AsyncSession = Depends(get_session),
):
    """Reject a post (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject post with status '{post.status}'",
        )
    
    post.status = "rejected"
    post.reviewed_by = "admin"
    post.reviewed_at = datetime.utcnow()
    post.rejection_reason = request.reason
    
    await session.commit()
    await session.refresh(post)
    
    return PostReviewResponse(
        post_id=post.id,
        status=post.status,
        reviewed_by=post.reviewed_by,
        reviewed_at=post.reviewed_at,
    )


@router.post("/admin/posts/{post_id}/publish", response_model=PostPublishResponse, dependencies=[Depends(admin_only)])
async def publish_post(
    post_id: UUID,
    request: PostPublishRequest,
    session: AsyncSession = Depends(get_session),
):
    """Publish a post (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.status not in ["approved", "draft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish post with status '{post.status}'. Must be 'approved' or 'draft'.",
        )
    
    now = datetime.utcnow()
    post.status = "published"
    post.published_at = now
    
    # If scheduled and publish_now=True, clear scheduled_at
    if request.publish_now:
        post.scheduled_at = None
    
    await session.commit()
    await session.refresh(post)
    
    return PostPublishResponse(
        post_id=post.id,
        status=post.status,
        published_at=post.published_at,  # type: ignore
    )


@router.post("/admin/posts/{post_id}/unpublish", response_model=PostPublishResponse, dependencies=[Depends(admin_only)])
async def unpublish_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Unpublish a post (archive it) (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    post.status = "archived"
    post.published_at = None
    
    await session.commit()
    await session.refresh(post)
    
    return PostPublishResponse(
        post_id=post.id,
        status=post.status,
        published_at=post.published_at,  # type: ignore
    )


@router.post("/admin/posts/{post_id}/schedule", response_model=PostScheduleResponse, dependencies=[Depends(admin_only)])
async def schedule_post(
    post_id: UUID,
    request: PostScheduleRequest,
    session: AsyncSession = Depends(get_session),
):
    """Schedule a post for future publication (admin only)."""
    stmt = select(Post).where(Post.id == post_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    if post.status not in ["approved", "draft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot schedule post with status '{post.status}'. Must be 'approved' or 'draft'.",
        )
    
    if request.scheduled_at <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future",
        )
    
    post.scheduled_at = request.scheduled_at
    post.status = "approved"
    
    await session.commit()
    await session.refresh(post)
    
    return PostScheduleResponse(
        post_id=post.id,
        status=post.status,
        scheduled_at=post.scheduled_at,
    )
