from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user, login_manager
from forms.user import UserForm, LoginForm
from services.user import get_user
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


@bp.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with uow() as db:
            user = get_user(db, form=form)
            if user:
                # Example: Set session variable for logged-in user
                login_user(user, remember=form.remember_me.data)
                flash("Login successful.", "success")
                return render_template("base.html")  # Replace "dashboard" with your desired route
            else:
                flash("Invalid email or password.", "danger")
                render_template("user/login.html", form=form)
    return render_template("user/login.html", form=form)