import math

from flask import Blueprint, render_template, request, url_for
from flask_login import login_required

from core.db import uow
from services.base import _context, _invert_navbar_colors
from services.user import list_users_for_admin, count_users_for_admin
from utilities.decorators import role_validation

bp = Blueprint("admin_users", __name__, url_prefix="/users")


@bp.route("/dashboard")
@login_required
@role_validation("ADMIN")
def user_dashboard():
    admin_context = _invert_navbar_colors(_context())

    search_field = (request.args.get("field") or "email").lower()
    if search_field not in {"user_id", "email"}:
        search_field = "email"

    raw_query = request.args.get("q")
    search_query = (raw_query or "").strip()
    if not search_query:
        search_query = None

    page = request.args.get("page", default=1, type=int)
    page = max(page, 1)
    per_page = request.args.get("per_page", default=10, type=int)
    per_page = max(min(per_page, 50), 1)

    user_id_error = None
    if search_field == "user_id" and search_query:
        try:
            int(search_query)
        except (TypeError, ValueError):
            user_id_error = "User ID must be a number."

    with uow(readonly=True) as db:
        if user_id_error:
            total_count = 0
            summaries = []
        else:
            total_count = count_users_for_admin(
                db,
                search_field=search_field,
                search_value=search_query,
            )

            if total_count:
                total_pages = math.ceil(total_count / per_page)
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page
                summaries = list_users_for_admin(
                    db,
                    search_field=search_field,
                    search_value=search_query,
                    limit=per_page,
                    offset=offset,
                )
            else:
                total_pages = 1
                page = 1
                offset = 0
                summaries = []

    if not total_count:
        total_pages = 1
        offset = 0

    if summaries:
        start_index = offset + 1
        end_index = offset + len(summaries)
    else:
        start_index = 0
        end_index = 0

    query_args = {"page": page, "field": search_field}
    if search_query:
        query_args["q"] = search_query
    current_page_url = url_for("admin_users.user_dashboard", **query_args)

    admin_context.update(
        {
            "page_title": "User Management",
            "page_description": "Monitor, search, and review Bodhgriha member accounts with quick access to key trust and safety signals.",
            "users": summaries,
            "search_query": search_query or "",
            "search_field": search_field,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_count": total_count,
            "start_index": start_index,
            "end_index": end_index,
            "current_page_url": current_page_url,
            "user_id_error": user_id_error,
        }
    )

    return render_template("admin/user_management.html", **admin_context)
