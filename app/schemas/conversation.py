from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=100,
    )


class ConversationUpdate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=100,
    )


class ConversationResponse(BaseModel):
    id: int
    title: str
    user_id: int
    created_at: datetime