"""HTTP framing only; authentication runs before the paid stream starts."""
import json
from contextlib import aclosing
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_current_user
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService

router = APIRouter()


def get_chat_service() -> ChatService:
    return ChatService()


@router.post(
    "/chat",
    response_class=StreamingResponse,
    dependencies=[Depends(get_current_user, scope="function")],
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat(request: ChatRequest, service: ChatService = Depends(get_chat_service)):
    async def events():
        async with aclosing(service.stream(request)) as stream:
            async for event in stream:
                data = json.dumps(event.data, ensure_ascii=False)
                yield f"event: {event.event}\ndata: {data}\n\n"

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
