"""Public chat contracts; SSE data is serialized as JSON."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    thread_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    actions: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)


class ChatEvent(BaseModel):
    # Metadata events let a streaming client expose agent progress without parsing text.
    event: Literal[
        "message_delta",
        "route_selected",
        "context_retrieved",
        "completed",
        "error",
    ]
    data: dict
