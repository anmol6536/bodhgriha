# routes/schools.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from core.db import uow
from forms.school import SchoolRegisterForm
from models.yoga import YogaSchool as School
from services.base import _context

bp = Blueprint("schools", __name__, url_prefix="/schools")


@bp.route("/register", methods=["GET", "POST"])
@login_required
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
