from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional
from llm_connector import get_llm

# Define the state for the graph
class ChatState(TypedDict):
    user_query: str
    sql_result: Optional[str]
    rag_result: Optional[str]
    final_response: Optional[str]

# Placeholder functions for agents (no logic yet)
def query_router(state: ChatState) -> str:
    # Placeholder: decide whether to query SQL, RAG, or both
    pass

def sql_agent(state: ChatState) -> ChatState:
    # Placeholder: query SQLite database
    pass

def rag_agent(state: ChatState) -> ChatState:
    # Placeholder: query ChromaDB for wiki text
    pass

def summarizer(state: ChatState) -> ChatState:
    # Placeholder: combine results and generate response
    pass

# Create the graph
def create_graph():
    # Initialize LLM for use in agents
    llm = get_llm()

    graph = StateGraph(ChatState)

    # Add nodes
    graph.add_node("query_router", query_router)
    graph.add_node("sql_agent", sql_agent)
    graph.add_node("rag_agent", rag_agent)
    graph.add_node("summarizer", summarizer)

    # Add edges (placeholder routing)
    graph.add_edge(START, "query_router")
    # Conditional edges will be added later based on router logic
    graph.add_edge("sql_agent", "summarizer")
    graph.add_edge("rag_agent", "summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile()