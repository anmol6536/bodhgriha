from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import select, union_all

from core.db import uow
from models.sql.base import User
from models.sql.chat import Message
from services.base import _context, _invert_navbar_colors

bp = Blueprint("chat", __name__)

mask_email = lambda email: email[0] + "*****" + email.split("@")[-1] if email else "unknown"


def _retrieve_chat_history(db, user, receiver_id):
    """Return ordered chat history between the current user and receiver."""
    stmt = (
        select(Message)
        .where(
            Message.sender_id.in_([user.id, receiver_id]),
            Message.receiver_id.in_([user.id, receiver_id]),
        )
        .order_by(Message.sent_at.asc())
    )

    rows = db.execute(stmt).scalars().all()
    return [
        {
            "sender": mask_email(row.sender.email),
            "content": row.content,
            "timestamp": row.sent_at.isoformat() if row.sent_at else None,
        }
        for row in rows
    ]


def _retrieve_previous_chats(db, user):
    """Return a list of users the current user has chatted with."""
    sent_stmt = select(Message.receiver_id.label("user_id")).where(Message.sender_id == user.id)
    received_stmt = select(Message.sender_id.label("user_id")).where(Message.receiver_id == user.id)

    union_subq = union_all(sent_stmt, received_stmt).subquery()

    users_stmt = (
        select(User)
        .join(union_subq, User.id == union_subq.c.user_id)
        .distinct()
        .order_by(User.first_name, User.email)
    )

    users = db.execute(users_stmt).scalars().all()

    return [{"id": u.id, "email": mask_email(u.email), "first_name": u.first_name} for u in users]


@bp.route("/user/<int:receiver_id>")
@login_required
def chat(receiver_id: int):
    with uow(readonly=True) as db:
        history = _retrieve_chat_history(db, current_user, receiver_id)
        previous_chats = _retrieve_previous_chats(db, current_user)

    base_context = _invert_navbar_colors(_context())
    context = dict(
        receiver_id=receiver_id,
        reciever_id=receiver_id,
        chat_history=history,
        previous_chats=previous_chats,
        **base_context,
    )

    if request.headers.get("HX-Request"):
        return render_template("user/partials/chat_thread.html", **context)

    return render_template("user/chat.html", **context)
