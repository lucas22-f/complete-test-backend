from fastapi import APIRouter, Depends,HTTPException,status

from app.api.dependencies import get_current_user
from app.models.user import User
from app.repositories.message import MessageRepository
router= APIRouter()

from app.repositories.conversation import ConversationRepository
from app.services.conversations import ConversationService
from app.schemas.conversation import ConversationCreate,ConversationResponse, ConversationUpdate


from sqlalchemy.orm import Session
from app.db.dependencies import db_get

db = db_get()

def build_service(db:Session)->ConversationService:
    return ConversationService(
        ConversationRepository(db)
    )

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(db_get),
):
    service = build_service(db)

    return service.create_conversation(
        request,
        current_user.id,
    )

@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(db_get),
):
    service = build_service(db)

    conversation = service.get_conversation(
        conversation_id,
        current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation

@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
)
def list_conversations(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(db_get),
):
    service = build_service(db)

    return service.list_conversations(
        current_user.id
    )


@router.patch("/conversations/{conversation_id}")
def update_title(conversation_id:int,request:ConversationUpdate,db:Session = Depends(db_get),current_user: User= Depends(get_current_user)):
    service = build_service(db)

    conversation =  service.update_conversation(
        conversation_id=conversation_id,
        current_user_id=current_user.id,
        title=request.title,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not Found"
        )

    return conversation



@router.delete("/conversations/{conversation_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_conver(conversation_id:int,db:Session = Depends(db_get),current_user:User = Depends(get_current_user)):
    service = build_service(db)

    res = service.delete_conversation(conversation_id,current_user.id)

    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation Not Found"
        )

    return None

