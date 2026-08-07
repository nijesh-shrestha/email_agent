from sqlalchemy import ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    provider: Mapped[str] = mapped_column(default="google")

    access_token: Mapped[str] = mapped_column(Text)

    refresh_token: Mapped[str] = mapped_column(Text)

    expires_at: Mapped[DateTime] = mapped_column(DateTime)

    scope: Mapped[str] = mapped_column(Text)

    user = relationship("User")