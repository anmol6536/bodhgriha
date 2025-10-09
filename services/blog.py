# services/blog_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from models.sql.base import BlogPost, User
from utilities.parsers.mdown import parse_markdown
from services.user import _resolve_user


def register_blog(
        db: Session,
        *,
        slug: str,
        body_md: str
) -> BlogPost:
    """
    Create a BlogPost from markdown + front matter.

    - Uses parse_markdown() → (meta, body_html, body_text)
    - Enforces unique slug (case-insensitive)
    - Sets is_published / published_at based on meta.draft and meta.published_at
    """
    # Enforce unique slug (case-insensitive) up front
    exists = db.scalar(select(BlogPost.id).where(func.lower(BlogPost.slug) == slug.lower()))
    if exists:
        raise ValueError("slug_exists")

    meta, body_html, body_text = parse_markdown(body_md)

    is_published = not bool(meta.pop("draft", False))
    published_at = meta.pop("published_at")
    author = _resolve_user(db, email=meta.pop("author"))

    if is_published and not published_at:
        published_at = datetime.now(timezone.utc)

    title = meta.pop("title")

    post = BlogPost(
        slug=slug,
        title=title,
        body_md=body_md,
        body_html=body_html,
        body_text=body_text,
        meta=meta,
        is_published=is_published,
        published_at=published_at,
        author=author,
    )
    db.add(post)
    try:
        db.flush()  # assign id without committing
    except IntegrityError as ie:
        db.rollback()
        # race on unique index
        raise ValueError("slug_exists") from ie

    return post


def get_all_blogs(
        db: Session,
        *,
        published_only: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
) -> Sequence[BlogPost]:
    """
    Retrieve blog posts, newest first.
    Set published_only=False to include drafts.
    """
    stmt = select(BlogPost).options(selectinload(BlogPost.author))
    if published_only:
        stmt = stmt.where(BlogPost.is_published.is_(True))
    stmt = stmt.order_by(BlogPost.published_at.desc().nullslast(), BlogPost.id.desc())
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def delete_blog_by_id(db: Session, blog_id: int) -> None:
    """
    Delete a blog post by its ID.
    """
    post = db.get(BlogPost, blog_id)
    if post:
        db.delete(post)
        db.flush()  # apply deletion without committing
    else:
        raise ValueError("Blog post not found.")


def publish_blog(db: Session, blog_id: int) -> BlogPost:
    """
    Mark a blog post as published and set published_at if missing.
    """
    post = db.get(BlogPost, blog_id)
    if not post:
        raise ValueError("Blog post not found.")

    post.is_published = True
    if not post.published_at:
        post.published_at = datetime.now(timezone.utc)

    db.flush()
    return post


def unpublish_blog(db: Session, blog_id: int) -> BlogPost:
    """
    Mark a blog post as unpublished and clear published_at timestamp.
    """
    post = db.get(BlogPost, blog_id)
    if not post:
        raise ValueError("Blog post not found.")

    post.is_published = False
    post.published_at = None

    db.flush()
    return post
