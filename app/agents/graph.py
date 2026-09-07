"""Build the smallest explicit graph; inject the model for offline tests."""

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from app.agents.state import ChatState


def build_graph(model: BaseChatModel):
    async def respond(state: ChatState, config: RunnableConfig):
        # LangGraph forwards tokens while awaiting the model's complete result.
        response = await model.ainvoke(state["messages"], config=config)
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("model", respond)
    graph.add_edge(START, "model")
    graph.add_edge("model", END)
    # No checkpointer: thread_id is correlation only, not persistent memory.
    return graph.compile()
