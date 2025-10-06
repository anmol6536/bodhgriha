from __future__ import annotations

from flask import abort, make_response, render_template_string, request, url_for
from flask_login import current_user, login_required

from core.db import uow
from forms.user import AddressForm
from models.sql import Address
from services.user import save_address_from_form

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
