from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, HttpUrl, Field


class BlogMeta(BaseModel):
    """
    Blog post metadata, stored in BlogPost.meta (JSONB).
    Validates front matter extracted from Markdown.
    """
    __version__ = "1.0.0"   # schema version

    title: str
    slug: str
    author: Optional[str] = None
    draft: bool = False
    published_at: Optional[date] = None
    updated_at: Optional[date] = None
    tags: List[str] = Field(default_factory=list)
    hero_image: Optional[HttpUrl] = None
    description: Optional[str] = None

    social: Optional[Dict[str, str]] = None

    class Config:
        extra = "ignore"  # ignore unknown keys for forward compatibility
