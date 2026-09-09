"""Define la salida estructurada usada para decidir una ruta del grafo."""

from typing import Literal

from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    """Representa una decisión validada antes de que LangGraph cambie de nodo.

    ``Literal`` limita ``route`` a capacidades conocidas. Si el modelo devuelve
    otro valor, Pydantic lo rechaza en lugar de dejar que el grafo tome una ruta
    inválida. ``mcp`` figura desde ahora para conservar el contrato futuro, aunque
    el grafo actual todavía lo redirige de forma segura a la ruta directa.
    """

    route: Literal["direct", "rag", "mcp"]
    # Es una etiqueta breve de intención, no razonamiento del modelo ni dato público.
    reason: str = Field(description="Short internal intent label, not chain-of-thought.")
