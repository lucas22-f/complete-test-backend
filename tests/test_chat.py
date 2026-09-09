"""Offline proof of streaming, routing, RAG metadata, and safe failure paths."""

import asyncio
import json
import os

# Keep tests independent of developer credentials and database contents.
os.environ.setdefault("SECRET_KEY", "offline-test-secret-key-at-least-32-bytes")
os.environ["LANGSMITH_TRACING"] = "false"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from pydantic import ValidationError

from app.agents.routing import RouteDecision
from app.api.chat import get_chat_service, router
from app.api.dependencies import get_current_user
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService


async def direct_decider(_: str) -> RouteDecision:
    return RouteDecision(route="direct", reason="general")


async def rag_decider(_: str) -> RouteDecision:
    return RouteDecision(route="rag", reason="store_policy")


async def fake_retriever(_: str) -> tuple[str, list[dict]]:
    return "Returns are accepted within 10 days.", [{"source": "ecommerce_faq.pdf", "page": 1}]


def service(model, **kwargs) -> ChatService:
    return ChatService(
        model,
        route_decider=direct_decider,
        retrieve_context=fake_retriever,
        **kwargs,
    )


def collect(chat_service: ChatService, message: str = "Hello"):
    async def run():
        request = ChatRequest(thread_id="test", message=message)
        return [event async for event in chat_service.stream(request)]

    return asyncio.run(run())


def test_direct_route_streams_and_completes():
    events = collect(service(FakeListChatModel(responses=["Hi"])))
    assert [event.event for event in events] == [
        "route_selected", "message_delta", "message_delta", "completed",
    ]
    assert events[0].data == {"route": "direct"}
    assert events[-1].data == {
        "thread_id": "test", "response": "Hi", "actions": [], "sources": [],
    }


def test_rag_route_exposes_retrieval_metadata_and_sources():
    chat_service = ChatService(
        FakeListChatModel(responses=["You can return it within 10 days."]),
        route_decider=rag_decider,
        retrieve_context=fake_retriever,
    )
    events = collect(chat_service, "What is the returns policy?")
    assert events[0].event == "route_selected"
    assert events[1].event == "context_retrieved"
    assert events[-1].event == "completed"
    assert events[0].data == {"route": "rag"}
    assert events[1].data == {
        "actions": [{"type": "rag_retrieval", "status": "completed", "source_count": 1}],
        "sources": [{"source": "ecommerce_faq.pdf", "page": 1}],
    }
    assert events[-1].data["sources"] == events[1].data["sources"]
    assert events[-1].data["actions"] == events[1].data["actions"]


def test_partial_failure_is_sanitized_without_completion_or_retry():
    model = FakeListChatModel(responses=["Hello"], error_on_chunk_number=1)
    events = collect(service(model))
    assert [event.event for event in events] == ["route_selected", "message_delta", "error"]
    assert events[-1].data == {"code": "generation_failed"}


def test_timeout_is_terminal():
    events = collect(service(FakeListChatModel(responses=["Hi"], sleep=0.1)), timeout=0.01)
    assert [event.model_dump() for event in events] == [
        {"event": "error", "data": {"code": "generation_timeout"}}
    ]


def test_model_is_lazy_and_construction_failure_is_safe(monkeypatch):
    def unavailable(**kwargs):
        assert kwargs["model"] == "gpt-5-nano"
        assert kwargs["max_retries"] == 0
        raise RuntimeError("private provider details")

    monkeypatch.setattr("app.services.chat.ChatOpenAI", unavailable)
    chat_service = ChatService(route_decider=direct_decider, retrieve_context=fake_retriever)
    assert collect(chat_service)[0].model_dump() == {
        "event": "error", "data": {"code": "generation_failed"},
    }


def test_model_with_no_chunks_is_not_success():
    events = collect(service(FakeListChatModel(responses=[""])))
    assert events[-1].event == "error"
    assert events[-1].data == {"code": "generation_failed"}


def test_cancellation_propagates():
    async def run():
        chat_service = service(FakeListChatModel(responses=["Hi"], sleep=10))
        stream = chat_service.stream(ChatRequest(thread_id="t", message="Hello"))
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
    app.dependency_overrides[get_chat_service] = lambda: service(
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
    deltas = [item["delta"] for frame, item in zip(frames, data, strict=True) if frame.startswith("event: message_delta")]
    assert "".join(deltas) == "Hi\nthere"
