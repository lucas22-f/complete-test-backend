from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate


class ConversationRepository:

    def __init__(
        self,
        db: Session,    
    ):
        self.db = db

    def create(
        self,
        request: ConversationCreate,
        user_id: int,
    ) -> Conversation:

        conversation = Conversation(
            title=request.title,
            user_id=user_id,
        )

        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def list_by_user(
        self,
        user_id: int,
    ) -> list[Conversation]:

        return (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user_id
            )
            .all()
        )

    def get_by_id_and_user(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:

        return (
            self.db.query(Conversation)
            .filter(
                Conversation.id
                == conversation_id,
                Conversation.user_id
                == user_id,
            )
            .first()
        )

    def update_title(
        self,
        conversation_id: int,
        user_id: int,
        new_title: str,
    ) -> Conversation | None:

        conversation = (
            self.get_by_id_and_user(
                conversation_id,
                user_id,
            )
        )

        if conversation is None:
            return None

        conversation.title = new_title

        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def delete_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ) -> bool:

        conversation = (
            self.get_by_id_and_user(
                conversation_id,
                user_id,
            )
        )

        if conversation is None:
            return False

        self.db.delete(conversation)
        self.db.commit()

        return True