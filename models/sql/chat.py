# testimonials.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.sql.base import TimestampMixin

from pydantic import BaseModel, Field
from typing import Optional, List



class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (
        # Helpful indexes and table metadata
        dict(
            schema="content",
            comment="User-to-user messages",
        ),
    )

    id = mapped_column(BigInteger, primary_key=True)
    sender_id = mapped_column(Integer, ForeignKey("auth.users.id"), nullable=False)
    receiver_id = mapped_column(Integer, ForeignKey("auth.users.id"), nullable=False)
    content = mapped_column(Text, nullable=False)
    is_read = mapped_column(Boolean, nullable=False, server_default=text("false"))
    sent_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    read_at = mapped_column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")
