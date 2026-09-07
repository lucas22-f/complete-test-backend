"""Coordinate generation without exposing provider details to HTTP clients."""
import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from app.agents.graph import build_graph
from app.core.config import settings
from app.schemas.chat import ChatEvent, ChatRequest, ChatResponse


class ChatService:
    def __init__(self, model: BaseChatModel | None = None, timeout: float | None = None):
        self.model = model
        self.timeout = timeout if timeout is not None else settings.chat_timeout_seconds

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatEvent]:
        try:
            # Lazy construction keeps unrelated endpoints usable without an OpenAI key.
            model = self.model or ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                streaming=True,
                timeout=self.timeout,
                max_retries=0,  # Never replay generation after partial text was sent.
                max_completion_tokens=settings.chat_max_output_tokens,
            )
            graph = build_graph(model)
            fragments: list[str] = []
            async with asyncio.timeout(self.timeout):
                # Closing the iterator also closes graph work on client cancellation.
                async with aclosing(graph.astream(
                    {"messages": [("user", request.message)]},
                    stream_mode="messages", version="v2",
                )) as stream:
                    async for part in stream:
                        chunk, metadata = part["data"]
                        if metadata.get("langgraph_node") != "model":
                            continue
                        # Only public text, never reasoning or provider metadata.
                        text = chunk.text
                        if text:
                            fragments.append(text)
                            yield ChatEvent(event="message_delta", data={"delta": text})
            if not fragments:
                yield ChatEvent(event="error", data={"code": "empty_response"})
                return
            response = ChatResponse(thread_id=request.thread_id, response="".join(fragments))
            yield ChatEvent(event="completed", data=response.model_dump())
        except TimeoutError:
            yield ChatEvent(event="error", data={"code": "generation_timeout"})
        except Exception:
            # Cancellation is BaseException and propagates instead of becoming SSE.
            yield ChatEvent(event="error", data={"code": "generation_failed"})
