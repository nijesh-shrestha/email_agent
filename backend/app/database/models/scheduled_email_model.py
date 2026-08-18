from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.user_model import User


class ScheduledEmailStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledEmail(Base):
    """Model for storing scheduled emails that will be sent at a future time."""

    __tablename__ = "scheduled_emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    scheduled_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    status: Mapped[ScheduledEmailStatus] = mapped_column(
        Enum(ScheduledEmailStatus),
        default=ScheduledEmailStatus.PENDING,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
