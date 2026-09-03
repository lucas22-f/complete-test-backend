from sqlalchemy.orm import Session

from app.models.message import Message
from app.schemas.message import MessageCreate


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create( self,conversation_id: int,request: MessageCreate,) -> Message:

        message = Message(
            conversation_id=conversation_id,
            content=request.content,
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        return message

    def list_by_conversation(self,conversation_id: int,) -> list[Message]:
        
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .all()
        )