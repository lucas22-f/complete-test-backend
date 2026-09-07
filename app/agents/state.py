"""Only conversation messages belong to the first, stateless graph."""

from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    # Append messages and replace matching IDs instead of duplicating them.
    messages: Annotated[list[AnyMessage], add_messages]
