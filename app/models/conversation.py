from datetime import datetime
from sqlalchemy import ForeignKey, Integer,String,DateTime
from sqlalchemy.orm import Mapped,mapped_column, relationship

from typing import TYPE_CHECKING
from app.db.modeloBase import Base



if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.user import User




class Conversation(Base):
    """
    Modelo ORM de Conversation.

    Esta clase representa una tabla de la base de datos.
    Cada instancia representa una fila.
    """

    __tablename__ = "conversations"

    # Primary key.
    # SQLAlchemy/SQLite generará el ID automáticamente.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Título de la conversación.
    # nullable=False significa que no puede guardarse como NULL.
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    user: Mapped["User"] = relationship(
        back_populates="conversations"
    )


    created_at: Mapped[datetime] = mapped_column(DateTime,default=datetime.now,nullable=False)