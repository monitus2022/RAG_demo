from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional
from llm_connector import get_llm
from agents.sql_agent import sql_agent_node

# Define the state for the graph
class ChatState(TypedDict):
    user_query: str
    sql_result: Optional[str]
    rag_result: Optional[str]
    final_response: Optional[str]

def query_router(state: ChatState) -> ChatState:
    """Route query to appropriate agent based on content"""
    user_query = state.get("user_query", "").lower()

    # Simple routing logic - can be enhanced with LLM-based routing
    sql_keywords = ['price', 'average', 'count', 'sum', 'transaction', 'estate', 'building', 'unit']
    rag_keywords = ['what is', 'explain', 'about', 'definition', 'history']

    has_sql_keywords = any(keyword in user_query for keyword in sql_keywords)
    has_rag_keywords = any(keyword in user_query for keyword in rag_keywords)

    if has_sql_keywords and not has_rag_keywords:
        return {**state, "route": "sql_agent"}
    elif has_rag_keywords and not has_sql_keywords:
        return {**state, "route": "rag_agent"}
    else:
        # Default to SQL for now, can be enhanced
        return {**state, "route": "sql_agent"}

def sql_agent(state: ChatState) -> ChatState:
    """SQL agent node using custom pipeline"""
    result = sql_agent_node(state)
    return {**state, **result}

def rag_agent(state: ChatState) -> ChatState:
    # Placeholder: query ChromaDB for wiki text
    # For now, return placeholder result
    return {**state, "rag_result": "RAG functionality not yet implemented"}

def summarizer(state: ChatState) -> ChatState:
    """Combine results and generate final response"""
    sql_result = state.get("sql_result")
    rag_result = state.get("rag_result")

    # Simple combination logic - can be enhanced
    if sql_result and rag_result:
        final_response = f"SQL Results: {sql_result}\n\nRAG Results: {rag_result}"
    elif sql_result:
        final_response = sql_result
    elif rag_result:
        final_response = rag_result
    else:
        final_response = "No results found."

    return {**state, "final_response": final_response}

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

    # Add edges with conditional routing
    graph.add_edge(START, "query_router")

    # Conditional routing based on query_router decision
    graph.add_conditional_edges(
        "query_router",
        lambda result: result.get("route"),  # Extract route from state
        {
            "sql_agent": "sql_agent",
            "rag_agent": "rag_agent"
        }
    )

    # Both agents lead to summarizer
    graph.add_edge("sql_agent", "summarizer")
    graph.add_edge("rag_agent", "summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile()