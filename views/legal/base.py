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
from services.base import _context, _invert_navbar_colors

bp = Blueprint("legal", __name__, url_prefix="/legal")


@bp.route("/terms-and-privacy", methods=["GET"])
def terms():
    return render_template("legal/tos.html", **_invert_navbar_colors(_context()))
