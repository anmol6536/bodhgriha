from __future__ import annotations

from typing import Sequence, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from forms.school import SchoolRegisterForm
from models.yoga.base import YogaSchool


def list_schools(
        db: Session,
        *,
        include_inactive: bool = True,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
) -> Sequence[YogaSchool]:
    """
    Return schools ordered by newest first with owner eager-loaded.
    """
    stmt = select(YogaSchool).options(selectinload(YogaSchool.owner))
    if not include_inactive:
        stmt = stmt.where(YogaSchool.is_active.is_(True))
    if search:
        like_expr = f"%{search}%"
        stmt = stmt.where(YogaSchool.name.ilike(like_expr))
    stmt = stmt.order_by(YogaSchool.created_at.desc().nullslast(), YogaSchool.id.desc())
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def count_schools(
        db: Session,
        *,
        include_inactive: bool = True,
        search: Optional[str] = None,
) -> int:
    """
    Count schools matching the provided filters.
    """
    stmt = select(func.count()).select_from(YogaSchool)
    if not include_inactive:
        stmt = stmt.where(YogaSchool.is_active.is_(True))
    if search:
        like_expr = f"%{search}%"
        stmt = stmt.where(YogaSchool.name.ilike(like_expr))
    return db.scalar(stmt) or 0


def get_school(db: Session, school_id: int) -> YogaSchool | None:
    """
    Retrieve a single school by primary key.
    """
    return db.get(YogaSchool, school_id)


def update_school_from_form(
        db: Session,
        *,
        school: YogaSchool,
        form: SchoolRegisterForm
) -> YogaSchool:
    """
    Mutate a school instance based on validated form data.
    """
    school.name = form.name.data.strip()
    school.description = form.description.data or None
    school.email = (form.email.data or "").strip().lower()
    school.phone = form.phone.data or None
    school.website = form.website.data or None
    school.registration_number = form.registration_number.data or None
    school.certification_body = form.certification_body.data or None
    school.is_verified = bool(form.is_verified.data)
    school.is_active = bool(form.is_active.data)

    db.add(school)
    db.flush()
    return school
