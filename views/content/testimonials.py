from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import select
from werkzeug.utils import secure_filename
import os
import uuid

from core.db import uow
from forms.testimonials import TestimonialForm
from models.sql.testimonials import Testimonial
from models.sql.base import RoleBits
from utilities.decorators import role_validation
from services.base import _context

bp = Blueprint("testimonials", __name__, url_prefix="/testimonials")


def _save_uploaded_files(files):
    """Save uploaded files into static/uploads/testimonials and return public URLs."""
    urls = []
    if not files:
        return urls

    upload_dir = os.path.join(current_app.static_folder, "uploads", "testimonials")
    os.makedirs(upload_dir, exist_ok=True)

    for f in files:
        if not getattr(f, "filename", None):
            continue
        filename = secure_filename(f.filename)
        # prefix with UUID to avoid collisions
        name, ext = os.path.splitext(filename)
        dest_name = f"{uuid.uuid4().hex}{ext}"
        dest_path = os.path.join(upload_dir, dest_name)
        f.save(dest_path)
        urls.append(url_for("static", filename=f"uploads/testimonials/{dest_name}"))
    return urls


@bp.route("/register", methods=["GET", "POST"])  # submit testimonial
@login_required
def register():
    form = TestimonialForm()
    form.school_id.data = 1 # Temporary hardcoded school_id for testing

    if form.validate_on_submit():
        # Merge meta photos from FieldList and uploaded files
        meta = {}
        photos_from_meta = meta.get("photos") or []

        uploaded = request.files.getlist(form.photos_upload.name)
        uploaded_urls = _save_uploaded_files(uploaded)

        photos = []
        photos.extend(photos_from_meta)
        photos.extend(uploaded_urls)
        meta["photos"] = photos

        # Determine user_id: admins may submit for others via hidden field; regular users become the author
        user_id = None
        if current_user and getattr(current_user, "is_authenticated", False):
            if current_user.has_role(RoleBits.ADMIN) and form.user_id.data:
                try:
                    user_id = int(form.user_id.data)
                except Exception:
                    user_id = current_user.id
            else:
                user_id = getattr(current_user, "id", None)


        testimonial = Testimonial(
            user_id=user_id,
            school_id=1, # Temporary hardcoded school_id for testing
            # school_id=int(form.school_id.data), --- IGNORE ---
            course_id=int(form.course_id.data) if form.course_id.data else None,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            rating=int(form.rating.data),
            is_published=bool(form.is_published.data),
            meta=meta,
        )

        if testimonial.is_published:
            from datetime import datetime

            testimonial.published_at = datetime.utcnow()

        try:
            with uow() as db:
                db.add(testimonial)
                db.flush()
                new_id = testimonial.id
            flash("Testimonial submitted.", "success")
            return redirect(url_for("schools.detail", school_id=testimonial.school_id))
        except Exception as e:
            current_app.logger.exception("Error saving testimonial")
            flash("Failed to save testimonial.", "danger")

    # GET or validation failed: render template if available
    # The template may use your render_form macro to render the form
    context = _context()
    try:
        return render_template("schools/submit-testimonial.html", form=form, **context)
    except Exception:
        # Fallback: return a minimal HTML with the form rendered by macro if available
        return render_template("base.html", form=form, **context)


def _serialize(t: Testimonial):
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "rating": t.rating,
        "is_published": bool(t.is_published),
        "is_featured": bool(t.is_featured),
        "published_at": t.published_at.isoformat() if t.published_at else None,
        "meta": t.meta or {},
        "user_id": t.user_id,
        "school_id": t.school_id,
        "course_id": t.course_id,
    }


@bp.get("/by_user/<int:user_id>")
def by_user(user_id: int):
    """Retrieve testimonials submitted by a user. If requester is owner or admin, include unpublished; otherwise only published."""
    include_unpublished = False
    if current_user.is_authenticated:
        if current_user.has_role(RoleBits.ADMIN) or current_user.id == user_id:
            include_unpublished = True

    with uow(readonly=True) as db:
        q = select(Testimonial).where(Testimonial.user_id == user_id)
        if not include_unpublished:
            q = q.where(Testimonial.is_published.is_(True))
        q = q.order_by(Testimonial.published_at.desc().nullslast())
        rows = db.scalars(q).all()

    return jsonify([_serialize(r) for r in rows])


@bp.get("/by_school/<int:school_id>")
def by_school(school_id: int):
    """Retrieve testimonials for a school. Admins may see drafts."""
    include_unpublished = False
    if current_user.is_authenticated and current_user.has_role(RoleBits.ADMIN):
        include_unpublished = True

    with uow(readonly=True) as db:
        q = select(Testimonial).where(Testimonial.school_id == school_id)
        if not include_unpublished:
            q = q.where(Testimonial.is_published.is_(True))
        q = q.order_by(Testimonial.published_at.desc().nullslast())
        rows = db.scalars(q).all()

    return jsonify([_serialize(r) for r in rows])


@bp.get("/published")
def published():
    """Return recently published testimonials (public)."""
    limit = int(request.args.get("limit", 50))
    with uow(readonly=True) as db:
        q = select(Testimonial).where(Testimonial.is_published.is_(True)).order_by(Testimonial.published_at.desc().nullslast()).limit(limit)
        rows = db.scalars(q).all()
    return jsonify([_serialize(r) for r in rows])


@bp.get("/featured")
def featured():
    """Return featured testimonials (published & featured)."""
    limit = int(request.args.get("limit", 20))
    with uow(readonly=True) as db:
        q = select(Testimonial).where(Testimonial.is_published.is_(True), Testimonial.is_featured.is_(True)).order_by(Testimonial.published_at.desc().nullslast()).limit(limit)
        rows = db.scalars(q).all()
    return jsonify([_serialize(r) for r in rows])
