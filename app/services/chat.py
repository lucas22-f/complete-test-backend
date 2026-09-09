"""Servicio de aplicación que coordina el grafo y expone eventos de chat."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.agents.graph import (
    ContextRetriever,
    RouteDecider,
    build_graph,
    build_openai_route_decider,
)
from app.core.config import settings
from app.rag.retriever import retrieve_context as retrieve_rag_context
from app.schemas.chat import ChatEvent, ChatRequest, ChatResponse


class ChatService:
    """Punto de entrada de la aplicación para ejecutar el agente de chat."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        timeout: float | None = None,
        route_decider: RouteDecider | None = None,
        retrieve_context: ContextRetriever | None = None,
    ):
        # Permitimos inyectar falsos en tests y proveedores reales en producción.
        self.model = model
        self.timeout = timeout if timeout is not None else settings.chat_timeout_seconds
        self.route_decider = route_decider
        self.retrieve_context = retrieve_context

    def _build_rag_retriever(self) -> ContextRetriever:
        """Crea un adaptador que entrega la credencial sólo al módulo RAG al invocarlo."""
        if settings.openai_api_key is None:
            raise RuntimeError("OpenAI API key is required for RAG retrieval")
        api_key = settings.openai_api_key.get_secret_value()

        async def retrieve(question: str) -> tuple[str, list[dict]]:
            return await retrieve_rag_context(api_key, question)

        return retrieve

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatEvent]:
        """Ejecuta el grafo y produce eventos SSE a medida que llegan tokens."""
        try:
            # Construimos ChatOpenAI recién cuando se solicita un chat.
            # Así, importar la aplicación no exige una API key para otros endpoints.
            model = self.model or ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                streaming=True,
                timeout=self.timeout,
                # No repetimos una generación que ya pudo enviar texto al cliente.
                max_retries=0,
                max_completion_tokens=settings.chat_max_output_tokens,
            )
            route_decider = self.route_decider or build_openai_route_decider(model)
            retrieve_context = self.retrieve_context or self._build_rag_retriever()

            # El service compone dependencias; el router no conoce LangGraph ni RAG.
            graph = build_graph(model, route_decider, retrieve_context)
            fragments: list[str] = []
            actions: list[dict] = []
            sources: list[dict] = []

            # Este contexto cancela la ejecución si supera el tiempo máximo permitido.
            async with asyncio.timeout(self.timeout):
                # graph.astream devuelve un iterador asíncrono, no una lista.
                # aclosing garantiza que se llame aclose() al salir del bloque.
                async with aclosing(graph.astream(
                    {"messages": [("user", request.message)], "actions": [], "sources": []},
                    # messages entrega tokens; updates entrega ruta y metadatos públicos.
                    stream_mode=["messages", "updates"], version="v2",
                )) as stream:
                    async for part in stream:
                        if part["type"] == "messages":
                            chunk, metadata = part["data"]
                            if metadata.get("langgraph_node") != "respond":
                                continue
                            # Sólo exponemos texto público, nunca razonamiento ni metadatos internos.
                            text = chunk.text
                            if text:
                                fragments.append(text)
                                # yield pausa esta función y entrega el delta al router inmediatamente.
                                yield ChatEvent(event="message_delta", data={"delta": text})
                            continue

                        # Los updates son el canal para que el cliente visualice el trabajo del agente.
                        for node_name, update in part["data"].items():
                            if node_name == "classify":
                                yield ChatEvent(event="route_selected", data={"route": update["route"]})
                            elif node_name == "retrieve_rag":
                                actions = update["actions"]
                                sources = update["sources"]
                                yield ChatEvent(
                                    event="context_retrieved",
                                    data={"actions": actions, "sources": sources},
                                )

            if not fragments:
                yield ChatEvent(event="error", data={"code": "empty_response"})
                return

            # El evento final resume el texto y la evidencia para clientes que llegan tarde.
            response = ChatResponse(
                thread_id=request.thread_id,
                response="".join(fragments),
                actions=actions,
                sources=sources,
            )
            yield ChatEvent(event="completed", data=response.model_dump())
        except TimeoutError:
            # asyncio.timeout transforma cancelación interna en TimeoutError fuera del contexto.
            yield ChatEvent(event="error", data={"code": "generation_timeout"})
        except Exception:
            # La cancelación del cliente es BaseException y se propaga; no la convertimos en SSE.
            # Otros fallos devuelven un código seguro sin filtrar detalles internos.
            yield ChatEvent(event="error", data={"code": "generation_failed"})
