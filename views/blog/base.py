from flask import Blueprint, render_template, request, redirect, url_for, flash
from forms.blog import BlogUploadForm
from core.db import uow
from services.blog import register_blog
from utilities.parsers.mdown import parse_markdown
from utilities.decorators import role_validation
from flask_login import login_required
from services.base import _context, _invert_navbar_colors
from uuid import uuid4

bp = Blueprint("blog", __name__)


@bp.route("/upload", methods=["GET", "POST"])
@login_required
@role_validation("ADMIN")
def upload():
    form = BlogUploadForm()
    if form.validate_on_submit():
        try:

            f = form.md_file.data
            body_md = f.read().decode("utf-8", errors="replace")

            metadata, _, _ = parse_markdown(body_md)
            slug = metadata.pop("slug")
            
            with uow() as db:
                register_blog(db, slug=slug, body_md=body_md)  # attach author if you have it
        except Exception as e:
            flash(f"Error uploading blog: {str(e)}", "error")
            return redirect(url_for("blog.upload"))

        flash("Blog uploaded.", "success")
        return redirect(url_for("blog.upload"))

    return render_template("admin/register_blog_form.html", form=form, **_context())


@bp.route("/<string:slug>")
def view_blog(slug: str):
    from models.sql import BlogPost, User
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from sqlalchemy import func, literal

    slug = '/' + slug if not slug.startswith('/') else slug
    full_name = func.trim(
        func.concat(
            func.coalesce(func.nullif(User.first_name, ''), literal('')),
            literal(' '),
            func.coalesce(func.nullif(User.last_name, ''), literal(''))
        )
    ).label("author_name")

    with uow(readonly=True) as db:
        row = db.execute(
            select(BlogPost, full_name)
            .join(User, User.id == BlogPost.author_id, isouter=True)
            .options(selectinload(BlogPost.author))  # prefetch relationship; won’t lazy-load later
            .where(BlogPost.slug == slug, BlogPost.is_published.is_(True))
        ).mappings().first()

    if not row:
        flash("Blog not found.", "error")
        return redirect(url_for("index"))

    post = row["BlogPost"]
    author = row["author_name"]

    context = _invert_navbar_colors(_context())

    return render_template("blog/post.html", post=post, author_name=author, **context)
    

@bp.route("/images/<string:filename>")
def blog_image(filename: str):
    from flask import send_from_directory, current_app
    import os

    static_folder = current_app.config.get("STATIC_FOLDER", "static")
    image_dir = os.path.join(static_folder, "images", "blog")

    # Flask will automatically serve from the given directory relative to the project root
    return send_from_directory(image_dir, filename)


@bp.route("/")
def index():
    from services.blog import get_all_blogs

    # set navbar text to black instead of white
    context = _invert_navbar_colors(_context())

    with uow(readonly=True) as db:
        posts = get_all_blogs(db)

    blog_hero_title = "Rooted in Wisdom, Growing in Connection."
    blog_hero_subtitle = "Welcome to Bodhgriha’s journal ..a collection of voices and visions that celebrate the spirit of yoga in everyday life."

    return render_template("blog/index.html", 
                           blog_hero_title=blog_hero_title,
                           blog_hero_subtitle=blog_hero_subtitle,
                           posts=posts, 
                           **context)


@bp.route("/dashboard")
@login_required
@role_validation("ADMIN")
def dashboard():
    from services.blog import get_all_blogs
    admin_context = _invert_navbar_colors(_context())

    with uow(readonly=True) as db:
        posts = get_all_blogs(db, published_only=False)

    admin_context.update(
        {
            "posts": posts,
            "blog_page_title": "Blog Dashboard",
            "blog_dashboard_description": (
                "Review draft and published posts, manage visibility, "
                "and keep the Bodhgriha voice consistent."
            ),
        }
    )

    return render_template("blog/dashboard.html", **admin_context)


@bp.route("/publish/<int:blog_id>", methods=["POST"])
@login_required
@role_validation("ADMIN")
def publish_blog(blog_id: int):
    from services.blog import publish_blog as publish_blog_service

    redirect_to = request.form.get("next") or url_for("blog.dashboard")

    try:
        with uow() as db:
            publish_blog_service(db, blog_id)
        flash("Blog published.", "success")
    except ValueError:
        flash("Blog not found.", "error")
    except Exception as exc:
        flash(f"Error publishing blog: {exc}", "error")

    return redirect(redirect_to)


@bp.route("/unpublish/<int:blog_id>", methods=["POST"])
@login_required
@role_validation("ADMIN")
def unpublish_blog(blog_id: int):
    from services.blog import unpublish_blog as unpublish_blog_service

    redirect_to = request.form.get("next") or url_for("blog.dashboard")

    try:
        with uow() as db:
            unpublish_blog_service(db, blog_id)
        flash("Blog unpublished.", "success")
    except ValueError:
        flash("Blog not found.", "error")
    except Exception as exc:
        flash(f"Error unpublishing blog: {exc}", "error")

    return redirect(redirect_to)


@bp.route("/delete/<int:blog_id>", methods=["POST"])
@login_required
@role_validation("ADMIN")
def delete_blog(blog_id: int):
    from services.blog import delete_blog_by_id

    redirect_to = request.form.get("next") or url_for("blog.dashboard")

    try:
        try:
            with uow() as db:
                delete_blog_by_id(db, blog_id)
        except ValueError as ve:
            flash(f"Error deleting blog: {str(ve)}", "error")
            return redirect(redirect_to)
        flash("Blog deleted.", "success")
    except Exception as e:
        flash(f"Error deleting blog: {str(e)}", "error")

    return redirect(redirect_to)
