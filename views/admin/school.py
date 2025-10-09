# routes/schools.py
import math

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from core.db import uow
from forms.school import SchoolRegisterForm
from models.yoga import YogaSchool as School
from services.base import _context, _invert_navbar_colors
from services.schools.base import list_schools, get_school, update_school_from_form, count_schools
from utilities.decorators import role_validation

bp = Blueprint("schools", __name__, url_prefix="/schools")


@bp.route("/register", methods=["GET", "POST"])
@login_required
@role_validation("INSTRUCTOR")  # only users with INSTRUCTOR role can register schools
def register():
    form = SchoolRegisterForm()

    if form.validate_on_submit():
        # Normalize inputs (do this before entering UoW)
        email = (form.email.data or "").strip().lower()

        try:
            with uow() as db:  # write UoW (transaction commits on exit)
                school = School(
                    owner_id=current_user.id,
                    name=form.name.data.strip(),
                    description=form.description.data or None,
                    email=email,
                    phone=form.phone.data or None,
                    website=form.website.data or None,
                    registration_number=form.registration_number.data or None,
                    certification_body=form.certification_body.data or None,
                    # is_verified False, is_active True from model defaults
                )
                db.add(school)
                db.flush()  # surface unique/constraint errors early; id assigned

                new_id = school.id
            flash("School registered successfully.", "success")
            return redirect(url_for("schools.detail", school_id=new_id))

        except IntegrityError as e:
            # Transaction already rolled back by uow(); show a friendly message.
            msg = "Could not register school. Email or registration number already exists."
            if "uq_schools_email" in str(e.orig):
                msg = "A school with this email already exists."
            elif "uq_schools_registration_number" in str(e.orig):
                msg = "This registration number is already registered."
            flash(msg, "danger")

    return render_template("schools/register.html", form=form, **_context())


@bp.route("/registered-schools")
@login_required
@role_validation("INSTRUCTOR")
def registered_schools():
    with uow(readonly=True) as db:
        schools = db.scalars(
            select(School)
            .where(School.owner_id == current_user.id)
            .order_by(School.name)
        ).all()
    return render_template("schools/registered-schools.html", schools=schools, **_context())


@bp.route("/<int:school_id>")
@login_required
def detail(school_id: int):
    with uow(readonly=True) as db:  # read-only snapshot, server-enforced
        school = db.get(School, school_id)

    if not school:
        flash("School not found.", "warning")
        return redirect(url_for("schools.register"))

    return render_template("schools/detail.html", school=school, **_context())


@bp.route("/school/dashboard")
@login_required
@role_validation("ADMIN")
def school_dashboard():
    admin_context = _invert_navbar_colors(_context())

    search_query = (request.args.get("q") or "").strip()
    page = request.args.get("page", default=1, type=int)
    page = max(page, 1)
    per_page = 8

    search_filter = search_query or None

    with uow(readonly=True) as db:
        total_count = count_schools(db, include_inactive=True, search=search_filter)
        if total_count:
            total_pages = math.ceil(total_count / per_page)
            if page > total_pages:
                page = total_pages
            offset = (page - 1) * per_page
            schools = list_schools(
                db,
                include_inactive=True,
                search=search_filter,
                limit=per_page,
                offset=offset,
            )
        else:
            total_pages = 1
            page = 1
            offset = 0
            schools = []

    forms = {}
    query_args = {"page": page}
    if search_query:
        query_args["q"] = search_query
    current_page_url = url_for("schools.school_dashboard", **query_args)

    for school in schools:
        form = SchoolRegisterForm(obj=school)
        form.is_verified.data = bool(school.is_verified)
        form.is_active.data = bool(school.is_active)
        form.next.data = current_page_url
        forms[school.id] = form

    if schools:
        start_index = offset + 1
        end_index = offset + len(schools)
    else:
        start_index = 0
        end_index = 0

    admin_context.update(
        {
            "schools": schools,
            "forms": forms,
            "page_title": "Host Dashboard",
            "page_description": "Review, verify, and update school partner profiles from a single glassy workspace.",
            "search_query": search_query,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "per_page": per_page,
            "start_index": start_index,
            "end_index": end_index,
        }
    )

    return render_template("admin/schools/dashboard.html", **admin_context)


@bp.route("/school/<int:school_id>/update", methods=["POST"])
@login_required
@role_validation("ADMIN")
def update_school(school_id: int):
    form = SchoolRegisterForm()

    if not form.validate_on_submit():
        flash("Please correct the highlighted errors before saving.", "error")
        return redirect(url_for("schools.school_dashboard"))

    try:
        with uow() as db:
            school = get_school(db, school_id)
            if not school:
                flash("School not found.", "error")
                return redirect(url_for("schools.school_dashboard"))

            update_school_from_form(db, school=school, form=form)

        flash("School details updated.", "success")
    except IntegrityError as exc:
        flash("Unable to update school. The email or registration number may already be in use.", "error")
    except Exception as exc:
        flash(f"Unexpected error updating school: {exc}", "error")

    next_url = form.next.data or request.form.get("next") or url_for("schools.school_dashboard")
    if not next_url.startswith("/"):
        next_url = url_for("schools.school_dashboard")

    return redirect(next_url)
