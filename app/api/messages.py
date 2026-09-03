from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import db_get
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.message import MessageCreate, MessageResponse
from app.services.message import MessageService


router = APIRouter()


def build_service(db: Session) -> MessageService:
    message_repository = MessageRepository(db)
    conversation_repository = ConversationRepository(db)

    return MessageService(
        message_repository=message_repository,
        conversation_repository=conversation_repository,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: int,
    request: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_get),
):
    service = build_service(db)

    message = service.create_message(
        conversation_id,
        current_user.id,
        request,
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return message


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def list_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_get),
):
    service = build_service(db)

    messages = service.list_messages(conversation_id,current_user.id)

    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return messages