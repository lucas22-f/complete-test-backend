from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean,DateTime,String
from sqlalchemy.orm import mapped_column,Mapped,relationship

from app.db.modeloBase import Base


if TYPE_CHECKING:
    from app.models.conversation import Conversation


class User(Base):
    __tablename__ = "users"

    id:Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(100),
        default="user"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )


    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
    )