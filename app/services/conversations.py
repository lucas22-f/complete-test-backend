class ConversationService:

    def __init__(self, repository):
        self.repository = repository

    def create_conversation(
        self,
        request,
        user_id: int,
    ):
        return self.repository.create(
            request,
            user_id,
        )

    def list_conversations(
        self,
        user_id: int,
    ):
        return self.repository.list_by_user(
            user_id
        )

    def get_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ):
        return (
            self.repository.get_by_id_and_user(
                conversation_id,
                user_id,
            )
        )

    def update_conversation(
        self,
        conversation_id: int,
        user_id: int,
        title: str,
    ):
        return self.repository.update_title(
            conversation_id,
            user_id,
            title,
        )

    def delete_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ):
        return (
            self.repository.delete_conversation(
                conversation_id,
                user_id,
            )
        )