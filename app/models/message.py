from sqlalchemy import Integer,ForeignKey,DateTime
from sqlalchemy.orm import  Mapped,mapped_column,relationship
from app.db.modeloBase import Base
from typing import TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base):

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)

    content: Mapped[str]

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime,nullable=False,default=datetime.now)
