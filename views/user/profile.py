from __future__ import annotations

import io

from flask import abort, flash, make_response, render_template, render_template_string, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from core.db import uow
from forms.user import AddressForm, AvatarUploadForm
from models.sql import Address, Avatar
from services.content.avatar import prepare_avatar
from services.user import save_address_from_form, update_user_avatar

from .dashboard import bp


def _render_address_modal(*, form: AddressForm, editing: bool) -> str:
    """
    Render the address form modal using the shared form macro.
    """
    close_url = url_for("user.profile_address_modal", close=1)
    template = """
    {% from "ui/macros/form.html" import render_form %}
    <div class="fixed inset-0 z-50 flex items-center justify-center" id="address-modal-root">
        <div class="absolute inset-0 bg-emerald-950/70 backdrop-blur-sm"
             hx-get="{{ close_url }}"
             hx-target="#address-modal-container"
             hx-swap="innerHTML"></div>
        <div class="relative z-10 w-full max-w-xl rounded-3xl border border-white/10 bg-white/10 text-white shadow-2xl backdrop-blur-2xl">
            <div class="flex items-center justify-between border-b border-white/10 px-5 py-4">
                <h2 class="text-lg font-semibold">
                    {{ "Update address" if editing else "Add address" }}
                </h2>
                <button type="button"
                        class="text-white/60 transition hover:text-white"
                        hx-get="{{ close_url }}"
                        hx-target="#address-modal-container"
                        hx-swap="innerHTML">
                    <span class="sr-only">Close</span>
                    &times;
                </button>
            </div>
            <div class="px-5 py-5"
                 hx-boost="true"
                 hx-target="#address-modal-container"
                 hx-swap="innerHTML">
                {{ render_form(
                    form,
                    action=url_for('user.profile_address_modal'),
                    method='POST',
                    submit_label='Update address' if editing else 'Save address',
                    field_order=['line1', 'line2', 'city', 'state', 'postal_code', 'country_iso2', 'is_primary'],
                    form_classes='space-y-4',
                    grid_classes='grid grid-cols-1 gap-4',
                    submit_classes='w-full rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400'
                ) }}
            </div>
        </div>
    </div>
    """
    return render_template_string(template, form=form, editing=editing, close_url=close_url)


def _render_avatar_modal(*, form: AvatarUploadForm) -> str:
    """
    Render the avatar upload modal as a standalone template for HTMX.
    """
    close_url = url_for("user.profile_avatar_modal", close=1)
    preview_url = None
    if current_user.is_authenticated:
        meta = getattr(current_user, "meta", {}) or {}
        avatar_sha = meta.get("avatar_sha256")
        if avatar_sha:
            preview_url = url_for("user.avatar", user_id=current_user.id, v=avatar_sha)

    return render_template(
        "user/dashboard/avatar_modal.html",
        form=form,
        close_url=close_url,
        preview_url=preview_url,
    )


@bp.route("/profile/address-modal", methods=["GET", "POST"])
@login_required
def profile_address_modal():
    if request.args.get("close"):
        return ""

    editing = False

    if request.method == "GET":
        form = AddressForm()

        address_id = request.args.get("address_id")
        if address_id:
            try:
                address_pk = int(address_id)
            except (TypeError, ValueError):
                abort(404)

            with uow(readonly=True) as db:
                address = db.get(Address, address_pk)
                if not address or address.user_id != current_user.id:
                    abort(404)

            form = AddressForm(obj=address)
            form.id.data = str(address.id)
            form.user_id.data = str(address.user_id)
            editing = True
        else:
            form.user_id.data = str(current_user.id)

        return _render_address_modal(form=form, editing=editing)

    # POST
    form = AddressForm()
    if not form.user_id.data:
        form.user_id.data = str(current_user.id)

    if form.validate_on_submit():
        with uow() as db:
            save_address_from_form(db, form=form, user_id=current_user.id)
        response = make_response("", 204)
        response.headers["HX-Redirect"] = url_for("user.profile")
        return response

    editing = bool(form.id.data)
    return _render_address_modal(form=form, editing=editing), 400


@bp.route("/profile/avatar-modal", methods=["GET"])
@login_required
def profile_avatar_modal():
    if request.args.get("close"):
        return ""

    form = AvatarUploadForm()
    return _render_avatar_modal(form=form)


@bp.route("/avatar/upload", methods=["POST"])
@login_required
def upload_avatar():
    form = AvatarUploadForm()
    if form.validate_on_submit():
        avatar_file = form.avatar.data
        if not avatar_file:
            abort(400, "No file uploaded")

        file_bytes = avatar_file.read()
        if not file_bytes:
            abort(400, "Empty file uploaded")

        avatar_data = prepare_avatar(file_bytes)

        with uow() as db:
            update_user_avatar(db, user_id=current_user.id, avatar_data=avatar_data)
            flash("Avatar updated successfully", "success")

        response = make_response("", 204)
        response.headers["HX-Redirect"] = url_for("user.profile")
        return response

    return _render_avatar_modal(form=form), 400


@bp.route("/avatar/<int:user_id>")
@login_required
def avatar(user_id: int):
    with uow(readonly=True) as db:
        avatar = db.scalar(select(Avatar).where(Avatar.user_id == user_id))
        if not avatar:
            abort(404)

        return send_file(
            io.BytesIO(avatar.content),
            mimetype=avatar.content_type,
            download_name=f"user-{user_id}-avatar",
            max_age=0,
            last_modified=avatar.uploaded_at,
            conditional=True,
            etag=avatar.sha256,
        )
