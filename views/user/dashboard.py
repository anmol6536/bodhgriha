from flask import Blueprint, Response, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.db import uow
from models.sql import User as UserModel, Testimonial
from models.yoga.base import Course, YogaSchool, Instructors
from services.base import _context, _invert_navbar_colors
from services.user import dashboard_links

bp = Blueprint("user", __name__)


@bp.get("/")
def dashboard() -> Response:
    """User dashboard view"""
    return render_template("user/dashboard/index.html", sidebar=dashboard_links(), **_invert_navbar_colors(_context()))


@bp.get("/profile")
@login_required
def profile() -> Response:
    base_context = _context()

    with uow(readonly=True) as db:
        user_stmt = (
            select(UserModel)
            .options(
                selectinload(UserModel.addresses),
                selectinload(UserModel.avatar),
            )
            .where(UserModel.id == current_user.id)
        )
        user = db.execute(user_stmt).scalar_one()

        addresses = list(user.addresses)

        testimonials_stmt = (
            select(Testimonial)
            .options(selectinload(Testimonial.school))
            .where(Testimonial.user_id == user.id)
        )
        testimonials = db.execute(testimonials_stmt).scalars().all()

        owned_schools_stmt = select(YogaSchool).where(YogaSchool.owner_id == user.id)
        owned_schools = db.execute(owned_schools_stmt).scalars().all()

        courses_stmt = (
            select(Course)
            .options(selectinload(Course.school))
            .join(Instructors, Course.id == Instructors.c.course_id)
            .where(Instructors.c.user_id == user.id)
        )
        teaching_courses = db.execute(courses_stmt).scalars().all()

    avatar_obj = getattr(user, "avatar", None)
    if isinstance(avatar_obj, list):
        avatar_obj = avatar_obj[0] if avatar_obj else None

    avatar_version = None
    if avatar_obj:
        avatar_version = avatar_obj.sha256
    elif user.meta:
        avatar_version = user.meta.get("avatar_sha256")

    avatar_url = url_for("user.avatar", user_id=user.id, v=avatar_version) if avatar_version else None

    base_context.update(
        addresses=addresses,
        testimonials=testimonials,
        owned_schools=owned_schools,
        teaching_courses=teaching_courses,
        user_avatar_url=avatar_url,
    )

    return render_template(
        "user/dashboard/profile.html",
        sidebar=dashboard_links(),
        **_invert_navbar_colors(base_context),
    )
