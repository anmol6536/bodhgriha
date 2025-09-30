from flask import Blueprint, render_template, request, redirect, url_for, flash
from forms.blog import BlogUploadForm
from core.db import uow
from services.blog import register_blog
from utilities.parsers.mdown import parse_markdown

bp = Blueprint("blog_admin", __name__)


@bp.route("/upload", methods=["GET", "POST"])
def upload_blog():
    form = BlogUploadForm()
    if form.validate_on_submit():
        f = form.md_file.data
        body_md = f.read().decode("utf-8", errors="replace")

        metadata, _, _ = parse_markdown(body_md)
        slug = metadata.pop("slug")

        with uow() as db:
            register_blog(db, slug=slug, body_md=body_md)  # attach author if you have it

        flash("Blog uploaded.", "success")
        return redirect(url_for("blog_admin.upload_blog"))

    return render_template("admin/register_blog_form.html", form=form)
