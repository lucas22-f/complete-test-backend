from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.message import MessageCreate, MessageResponse


class MessageService:
    def __init__(
        self,
        message_repository: MessageRepository,
        conversation_repository: ConversationRepository,
    ):
        self.message_repository = message_repository
        self.conversation_repository = conversation_repository

    def create_message(self,conversation_id: int,user_id:int ,request: MessageCreate,) -> MessageResponse | None:

        conversation = self.conversation_repository.get_by_id_and_user(
            conversation_id,
            user_id = user_id
        )

        if conversation is None:
            return None

        message = self.message_repository.create(
            conversation_id,
            request,
        )

        return MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            content=message.content,
            created_at=message.created_at,
        )

    def list_messages(
        self,
        conversation_id: int,
        user_id:int
    ) -> list[MessageResponse] | None:

        conversation = self.conversation_repository.get_by_id_and_user(
            conversation_id,
            user_id
        )

        if conversation is None:
            return None

        messages = self.message_repository.list_by_conversation(
            conversation_id
        )

        return [
            MessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ]