# testimonials.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.sql.base import TimestampMixin
from models.yoga.base import YogaSchool

from pydantic import BaseModel, Field
from typing import Optional, List


class Testimonial(TimestampMixin, Base):
    __tablename__ = "testimonials"
    __table_args__ = (
        # Helpful indexes and table metadata
        Index("ix_testimonials_published", "is_published", "published_at"),
        Index("ix_testimonials_featured", "is_featured"),
        Index("ix_testimonials_school", "school_id"),
        Index("ix_testimonials_course", "course_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_testimonials_rating_range"),
        dict(
            schema="content",
            comment="User testimonials for schools/courses with rating and publish state",
        ),
    )

    # PK
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # References
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("admin.schools.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("courses.courses.id", ondelete="SET NULL"), nullable=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Rating 1..5
    rating: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("5"))

    # Publishing
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Arbitrary extra data (e.g., locale, photos, context)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # Relationships
    user = relationship("User")
    school = relationship("YogaSchool")
    course = relationship("Course")

    def __repr__(self) -> str:
        return f"<Testimonial id={self.id} school_id={self.school_id} rating={self.rating} published={self.is_published}>"


class TestimonialMeta(BaseModel):
    """
    Pydantic model for Testimonial meta field.
    """
    __version__ = "1.0.0"  # schema version

    locale: Optional[str] = 'en-US'  # e.g., "en-US"
    photos: List[str] = Field(default_factory=list)  # URLs to photos
    context: Optional[str] = None  # e.g., "After completing the 200-hour YTT program..."

    class Config:
        extra = "ignore"  # ignore unknown keys for forward compatibility
