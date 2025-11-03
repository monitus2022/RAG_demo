from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional
from llm_connector import get_llm
from agents.sql_agent import sql_agent_node
from agents.rag_agent import rag_agent_node

# Define the state for the graph
class ChatState(TypedDict):
    user_query: str
    routes: Optional[list]
    sql_result: Optional[str]
    rag_result: Optional[str]
    final_response: Optional[str]

def query_router(state: ChatState) -> ChatState:
    """Route query to appropriate agent(s) using LLM-based classification"""
    user_query = state.get("user_query", "")

    # Get LLM for routing decision
    llm = get_llm()

    # Import routing prompt
    from prompts.routing_prompts import ROUTING_PROMPT

    # Format prompt with user query
    routing_prompt = ROUTING_PROMPT.format(user_query=user_query)

    try:
        # Get routing decision from LLM
        response = llm.invoke(routing_prompt).strip().upper()

        # Determine routes based on response
        if response == "BOTH":
            routes = ["sql_agent", "rag_agent"]
        elif response == "SINGLE_SQL":
            routes = ["sql_agent"]
        elif response == "SINGLE_RAG":
            routes = ["rag_agent"]
        else:
            # Fallback to keyword-based routing
            sql_keywords = ['price', 'average', 'count', 'sum', 'transaction', 'estate', 'building', 'unit', 'address', 'location', 'statistics', 'data']
            rag_keywords = ['what is', 'explain', 'about', 'definition', 'history', 'how', 'why', 'background', 'context']

            has_sql_keywords = any(keyword in user_query.lower() for keyword in sql_keywords)
            has_rag_keywords = any(keyword in user_query.lower() for keyword in rag_keywords)

            if has_sql_keywords and has_rag_keywords:
                routes = ["sql_agent", "rag_agent"]  # Both keywords present
            elif has_sql_keywords:
                routes = ["sql_agent"]
            elif has_rag_keywords:
                routes = ["rag_agent"]
            else:
                routes = ["sql_agent"]  # Default fallback

        return {**state, "routes": routes}

    except Exception as e:
        # If LLM routing fails, use keyword fallback
        sql_keywords = ['price', 'average', 'count', 'sum', 'transaction', 'estate', 'building', 'unit', 'address', 'location', 'statistics', 'data']
        rag_keywords = ['what is', 'explain', 'about', 'definition', 'history', 'how', 'why', 'background', 'context']

        has_sql_keywords = any(keyword in user_query.lower() for keyword in sql_keywords)
        has_rag_keywords = any(keyword in user_query.lower() for keyword in rag_keywords)

        if has_sql_keywords and has_rag_keywords:
            routes = ["sql_agent", "rag_agent"]
        elif has_sql_keywords:
            routes = ["sql_agent"]
        elif has_rag_keywords:
            routes = ["rag_agent"]
        else:
            routes = ["sql_agent"]

        return {**state, "routes": routes}

def sql_agent(state: ChatState) -> ChatState:
    """SQL agent node using custom pipeline"""
    result = sql_agent_node(state)
    return result

def rag_agent(state: ChatState) -> ChatState:
    """RAG agent node using custom pipeline"""
    result = rag_agent_node(state)
    return result

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

    # Conditional routing based on query_router decision - now supports multiple routes
    def route_to_agents(state):
        routes = state.get("routes", ["sql_agent"])  # Default to sql_agent if no routes
        return routes

    # Add conditional edges for routing
    graph.add_conditional_edges(
        "query_router",
        route_to_agents,
        {
            "sql_agent": "sql_agent",
            "rag_agent": "rag_agent"
        }
    )

    # Add edges from agents to summarizer (both can run in parallel)
    graph.add_edge("sql_agent", "summarizer")
    graph.add_edge("rag_agent", "summarizer")

    # Both agents lead to summarizer
    graph.add_edge("sql_agent", "summarizer")
    graph.add_edge("rag_agent", "summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile()