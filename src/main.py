import sys
import os
sys.path.append(os.path.dirname(__file__))

from graph.graph import create_graph
from agents.sql_agent import get_sql_agent

def main():
    # Initialize the Langgraph
    graph = create_graph()
    # Placeholder: future logic for running the chatbot
    print("Langgraph framework initialized.")

    # Test SQL agent
    print("\n--- Testing SQL Agent ---")
    agent = get_sql_agent()
    query = 'What is the average price of transactions in Lohas Park?'
    result = agent.query(query)
    print('Query:', query)
    print('Result:', result)

# Example usage
if __name__ == "__main__":
    main()