"""Offline proof of real graph streaming, SSE framing, and safe failure paths."""

import asyncio
import json
import os

# Keep tests independent of developer credentials and database contents.
os.environ.setdefault("SECRET_KEY", "offline-test-secret")
os.environ["LANGSMITH_TRACING"] = "false"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from pydantic import ValidationError

from app.api.chat import get_chat_service, router
from app.api.dependencies import get_current_user
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService


def collect(service):
    async def run():
        return [event async for event in service.stream(
            ChatRequest(thread_id="test", message="Hello")
        )]
    return asyncio.run(run())


def test_real_graph_streams_and_completes():
    events = collect(ChatService(FakeListChatModel(responses=["Hi"])))
    assert [e.event for e in events] == ["message_delta", "message_delta", "completed"]
    assert events[-1].data == {
        "thread_id": "test", "response": "Hi", "actions": [], "sources": [],
    }


def test_partial_failure_is_sanitized_without_completion_or_retry():
    model = FakeListChatModel(responses=["Hello"], error_on_chunk_number=1)
    events = collect(ChatService(model))
    assert [e.event for e in events] == ["message_delta", "error"]
    assert events[-1].data == {"code": "generation_failed"}


def test_timeout_is_terminal():
    events = collect(ChatService(FakeListChatModel(responses=["Hi"], sleep=0.1), timeout=0.01))
    assert [e.model_dump() for e in events] == [
        {"event": "error", "data": {"code": "generation_timeout"}}
    ]


def test_model_is_lazy_and_construction_failure_is_safe(monkeypatch):
    def unavailable(**kwargs):
        assert kwargs["model"] == "gpt-5-nano"
        assert kwargs["max_retries"] == 0
        raise RuntimeError("private provider details")

    monkeypatch.setattr("app.services.chat.ChatOpenAI", unavailable)
    service = ChatService()  # Constructor must not call OpenAI.
    assert collect(service)[0].model_dump() == {
        "event": "error", "data": {"code": "generation_failed"},
    }


def test_model_with_no_chunks_is_not_success():
    events = collect(ChatService(FakeListChatModel(responses=[""])))
    assert events[-1].event == "error"
    # LangChain rejects a stream with no generations before graph completion.
    assert events[-1].data == {"code": "generation_failed"}


def test_cancellation_propagates():
    async def run():
        service = ChatService(FakeListChatModel(responses=["Hi"], sleep=10))
        stream = service.stream(ChatRequest(thread_id="t", message="Hello"))
        task = asyncio.create_task(anext(stream))
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await stream.aclose()
    asyncio.run(run())


@pytest.mark.parametrize("message", ["", "   ", "x" * 8001])
def test_invalid_message(message):
    with pytest.raises(ValidationError):
        ChatRequest(thread_id="t", message=message)


def test_endpoint_auth_and_sse_contract():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_chat_service] = lambda: ChatService(
        FakeListChatModel(responses=["Hi\nthere"])
    )
    client = TestClient(app)
    payload = {"thread_id": "t", "message": "Hello"}
    assert client.post("/api/v1/chat", json=payload).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: object()
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = response.text.strip().split("\n\n")
    data = [json.loads(frame.split("\ndata: ", 1)[1]) for frame in frames]
    assert frames[-1].startswith("event: completed\n")
    assert data[-1]["response"] == "Hi\nthere"
    assert "".join(item["delta"] for item in data[:-1]) == "Hi\nthere"
