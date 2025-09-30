from flask import Blueprint, render_template, request, redirect, url_for, flash
from forms.user import UserForm
from core.db import uow
from services.user import add_user

bp = Blueprint("user", __name__)


@bp.route("/new", methods=["GET", "POST"])
def new_user():
    form = UserForm()
    if form.validate_on_submit():
        with uow() as db:
            add_user(
                db,
                email=form.email.data,
                password=form.password.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
            )
        flash("User created successfully.", "success")
    return render_template("admin/register_users_form.html", form=form)
