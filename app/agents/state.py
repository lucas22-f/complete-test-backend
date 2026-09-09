"""Declara el estado tipado que todos los nodos comparten dentro de LangGraph."""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """Contrato de datos que circula entre los nodos durante una ejecución.

    ``TypedDict`` no es una clase de dominio ni una base de datos: documenta y
    valida estáticamente qué claves entrega y consume cada nodo del grafo.
    """

    # ``Annotated`` asocia el reducer ``add_messages`` a esta clave. En vez de
    # reemplazar todo el historial, LangGraph agrega mensajes y reemplaza aquellos
    # que ya tengan el mismo ID, evitando duplicados.
    messages: Annotated[list[AnyMessage], add_messages]
    # ``Literal`` restringe la ruta a opciones declaradas. MCP se reserva para una
    # etapa posterior; tenerlo en el estado evita cambiar el contrato más adelante.
    route: Literal["direct", "rag", "mcp"]
    # Metadatos públicos de ejecución para la respuesta SSE; nunca secretos ni
    # razonamiento interno del modelo.
    actions: list[dict]
    sources: list[dict]
