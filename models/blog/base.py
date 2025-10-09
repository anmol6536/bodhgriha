from __future__ import annotations
from datetime import date
from typing import Optional, List, Dict
from pydantic import BaseModel, HttpUrl, Field, validator


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


class BlogDashboardFilters(BaseModel):
    """
    Encapsulates query parameters for the blog dashboard.
    Provides sanitized pagination + search data for downstream services.
    """

    field: str = "title"
    query: Optional[str] = None
    page: int = 1
    per_page: int = 10

    @validator("field", pre=True, always=True)
    def normalize_field(cls, value: Optional[str]) -> str:
        allowed = {"title", "slug", "all"}
        val = (value or "title").strip().lower()
        if val not in allowed:
            return "title"
        return val

    @validator("page", pre=True, always=True)
    def clamp_page(cls, value: int) -> int:
        try:
            page_int = int(value)
        except (TypeError, ValueError):
            return 1
        return max(page_int, 1)

    @validator("per_page", pre=True, always=True)
    def clamp_per_page(cls, value: int) -> int:
        try:
            per_page_int = int(value)
        except (TypeError, ValueError):
            return 10
        return min(max(per_page_int, 1), 50)

    @property
    def normalized_query(self) -> Optional[str]:
        if self.query is None:
            return None
        trimmed = self.query.strip()
        return trimmed or None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class BlogPaginationView(BaseModel):
    """
    Provides pagination metadata to render dashboard controls.
    """

    total_count: int = 0
    page: int = 1
    per_page: int = 10

    @property
    def total_pages(self) -> int:
        if self.total_count == 0:
            return 1
        return ((self.total_count - 1) // self.per_page) + 1

    @property
    def has_multiple_pages(self) -> bool:
        return self.total_pages > 1

    def clamp_page(self) -> "BlogPaginationView":
        """
        Return a copy with the page number clamped within valid bounds.
        """
        page = self.page
        if self.total_pages == 0:
            page = 1
        else:
            page = min(max(page, 1), self.total_pages)
        return self.copy(update={"page": page})

    def range_indices(self, current_page_count: int) -> tuple[int, int]:
        if current_page_count == 0 or self.total_count == 0:
            return 0, 0
        start = (self.page - 1) * self.per_page + 1
        end = start + current_page_count - 1
        return start, end
