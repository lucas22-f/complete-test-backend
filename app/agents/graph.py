"""Construye el grafo conversacional explícito con rutas directa y RAG.

El router HTTP no conoce estos nodos: solamente el servicio invoca el grafo.
Así se puede probar cada dependencia por separado y añadir nuevas capacidades sin
acoplar LangGraph a FastAPI.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.agents.routing import RouteDecision
from app.agents.state import ChatState

# Estos alias describen contratos, no crean funciones. ``Callable`` indica qué
# argumentos recibe la función y ``Awaitable`` que su resultado se obtiene con
# ``await``. Inyectarlos permite sustituir el LLM o el RAG por dobles en tests.
RouteDecider = Callable[[str], Awaitable[RouteDecision]]
ContextRetriever = Callable[[str], Awaitable[tuple[str, list[dict]]]]

ROUTER_PROMPT = """Classify the user's latest message.
Choose `rag` only for questions about the Demo Store ecommerce FAQ: shipping,
tracking, payment methods, exchanges, returns, or support hours.
Choose `direct` for every other conversational or general question.
MCP is not enabled in this graph slice, so never choose `mcp`.
Return a short intent label in `reason`; do not include hidden reasoning."""
# El clasificador devuelve datos estructurados validados por ``RouteDecision``;
# no es la respuesta que ve el usuario ni debe devolver razonamiento interno.

RAG_ANSWER_PROMPT = """You are the Demo Store support assistant.
Answer the user with the retrieved FAQ context below. Do not invent store policies.
If the context does not contain the answer, say so clearly and suggest contacting support.

Retrieved FAQ context:
{context}"""
# Este mensaje de sistema se agrega únicamente después de recuperar fragmentos
# del PDF. Por eso el modelo puede responder con evidencia y sin inventar reglas.


def _latest_user_message(messages: list[AnyMessage]) -> str:
    """Obtiene el último texto humano sin depender de FastAPI ni del request.

    El estado puede contener mensajes de sistema y respuestas previas. Recorrerlo
    desde el final garantiza que el router y el retriever trabajen sobre la última
    consulta real del usuario.
    """
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def build_graph(
    model: BaseChatModel,
    route_decider: RouteDecider,
    retrieve_context: ContextRetriever,
):
    """Compila el flujo LangGraph con dependencias externas inyectadas.

    El resultado es un runnable que el servicio ejecuta con ``ainvoke`` o
    ``astream``. El modelo, el clasificador y el recuperador se reciben desde
    afuera para mantener este módulo independiente de configuración y de HTTP.
    """

    async def classify(state: ChatState, _: RunnableConfig):
        """Clasifica la consulta y guarda la ruta que decidirá el siguiente nodo."""
        decision = await route_decider(_latest_user_message(state["messages"]))
        # MCP permanece en el contrato tipado para la siguiente etapa, pero no se
        # simula ni se invoca antes de contar con un nodo MCP real.
        route: Literal["direct", "rag"] = "rag" if decision.route == "rag" else "direct"
        return {"route": route}

    def select_route(state: ChatState) -> Literal["direct", "rag"]:
        """Devuelve la etiqueta que LangGraph usa para seguir una arista condicional."""
        return "rag" if state["route"] == "rag" else "direct"

    async def retrieve_rag(state: ChatState, _: RunnableConfig):
        """Busca contexto semántico y lo incorpora como instrucción para la respuesta."""
        context, sources = await retrieve_context(_latest_user_message(state["messages"]))
        return {
            # ``add_messages`` anexará este SystemMessage al historial del estado.
            "messages": [SystemMessage(content=RAG_ANSWER_PROMPT.format(context=context))],
            # Actions y sources son metadatos públicos para que el cliente muestre
            # qué capacidad se usó, sin revelar prompts, secretos ni razonamiento.
            "actions": [{"type": "rag_retrieval", "status": "completed", "source_count": len(sources)}],
            "sources": sources,
        }

    async def respond(state: ChatState, config: RunnableConfig):
        """Genera la respuesta final usando el historial y, si existe, el contexto RAG."""
        # LangGraph puede reenviar los tokens del modelo mientras espera el resultado.
        # El nodo RAG se ejecuta luego del mensaje humano, pero el proveedor espera
        # las instrucciones de sistema antes de la conversación que condicionan.
        system_messages = [message for message in state["messages"] if isinstance(message, SystemMessage)]
        conversation_messages = [message for message in state["messages"] if not isinstance(message, SystemMessage)]
        response = await model.ainvoke([*system_messages, *conversation_messages], config=config)
        return {"messages": [response]}

    # StateGraph define el estado compartido y el diagrama de ejecución; cada nodo
    # devuelve sólo las claves del estado que necesita actualizar.
    graph = StateGraph(ChatState)
    graph.add_node("classify", classify)
    graph.add_node("retrieve_rag", retrieve_rag)
    graph.add_node("respond", respond)
    graph.add_edge(START, "classify")
    # La salida de ``select_route`` elige entre responder directamente o recuperar
    # contexto primero. Esta es la bifurcación condicional explícita del grafo.
    graph.add_conditional_edges("classify", select_route, {"direct": "respond", "rag": "retrieve_rag"})
    graph.add_edge("retrieve_rag", "respond")
    graph.add_edge("respond", END)
    # Aún no hay checkpointer: por ahora thread_id es correlación, no memoria persistente.
    return graph.compile()


def build_openai_route_decider(model: BaseChatModel) -> RouteDecider:
    """Adapta structured output del modelo al contrato pequeño de enrutamiento.

    ``with_structured_output`` solicita una salida compatible con Pydantic, de
    modo que la decisión llega como ``RouteDecision`` y no como texto a parsear.
    """
    structured_model = model.with_structured_output(RouteDecision)

    async def decide(question: str) -> RouteDecision:
        """Envía sólo la última pregunta al clasificador para evitar rutas ambiguas."""
        return await structured_model.ainvoke([
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(content=question),
        ])

    return decide
