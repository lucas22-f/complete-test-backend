"""Servicio de aplicación que coordina el grafo y expone eventos de chat."""
import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from app.agents.graph import build_graph
from app.core.config import settings
from app.schemas.chat import ChatEvent, ChatRequest, ChatResponse


class ChatService:
    """Punto de entrada de la aplicación para ejecutar el agente de chat."""

    def __init__(self, model: BaseChatModel | None = None, timeout: float | None = None):
        # Permitimos inyectar un modelo falso en los tests y uno real en producción.
        self.model = model
        # El timeout también se puede sobrescribir en los tests o por configuración.
        self.timeout = timeout if timeout is not None else settings.chat_timeout_seconds

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
                # No repetimos automáticamente una generación que ya pudo enviar texto.
                max_retries=0,
                max_completion_tokens=settings.chat_max_output_tokens,
            )

            # El service conoce cómo construir el grafo; el router no conoce LangGraph.
            graph = build_graph(model)

            # Guardamos los fragmentos para poder emitir la respuesta completa al final.
            fragments: list[str] = []

            # Este contexto cancela la ejecución si supera el tiempo máximo permitido.
            async with asyncio.timeout(self.timeout):
                # graph.astream devuelve un iterador asíncrono, no una lista.
                # aclosing garantiza que se llame aclose() al salir del bloque.
                async with aclosing(graph.astream(
                    {"messages": [("user", request.message)]},
                    stream_mode="messages", version="v2",
                )) as stream:
                    # Cada iteración recibe un evento producido por LangGraph.
                    async for part in stream:
                        chunk, metadata = part["data"]

                        # Ignoramos eventos de otros nodos si el grafo crece en el futuro.
                        if metadata.get("langgraph_node") != "model":
                            continue

                        # Solo exponemos texto público, nunca razonamiento ni metadatos internos.
                        text = chunk.text
                        if text:
                            fragments.append(text)
                            # yield pausa esta función y entrega el delta inmediatamente al router.
                            yield ChatEvent(event="message_delta", data={"delta": text})

            # Si el proveedor no produjo texto, informamos un error explícito.
            if not fragments:
                yield ChatEvent(event="error", data={"code": "empty_response"})
                return

            # Unimos todos los fragmentos para que el cliente tenga también el resultado final.
            response = ChatResponse(thread_id=request.thread_id, response="".join(fragments))
            yield ChatEvent(event="completed", data=response.model_dump())
        except TimeoutError:
            # asyncio.timeout transforma la cancelación interna en TimeoutError fuera del contexto.
            yield ChatEvent(event="error", data={"code": "generation_timeout"})
        except Exception:
            # La cancelación del cliente es BaseException y se propaga; no la convertimos en SSE.
            # Para otros fallos devolvemos un código seguro sin filtrar detalles internos.
            yield ChatEvent(event="error", data={"code": "generation_failed"})
