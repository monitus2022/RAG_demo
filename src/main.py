import sys
import os
sys.path.append(os.path.dirname(__file__))

from graph.graph import create_graph
from logger import housing_logger as logger

def main():
    """Main entry point for the RAG Demo application with LangGraph orchestration"""

    try:
        # Initialize the LangGraph
        logger.info("Initializing LangGraph framework...")
        graph = create_graph()
        logger.info("LangGraph framework initialized successfully.")

        # Interactive chat loop
        print("\n🤖 RAG Demo Chatbot with LangGraph")
        print("Type 'quit' or 'exit' to end the conversation")
        print("-" * 50)

        while True:
            try:
                # Get user input
                user_query = input("\nYou: ").strip()

                if user_query.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye! 👋")
                    break

                if not user_query:
                    continue

                # Process through LangGraph
                logger.info(f"Processing user query: {user_query}")
                initial_state = {"user_query": user_query}

                result = graph.invoke(initial_state)

                # Display result
                final_response = result.get("final_response", "No response generated")
                print(f"\nAssistant: {final_response}")

                # Log the interaction
                logger.info(f"Query processed successfully: {user_query[:50]}...")

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                print(f"\n❌ Error: {str(e)}")
                print("Please try again.")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        print(f"❌ Failed to start application: {str(e)}")
        sys.exit(1)

def test_langgraph():
    """Test function for LangGraph integration"""
    print("\n--- Testing LangGraph Integration ---")

    try:
        graph = create_graph()

        # Test queries
        test_queries = [
            "What is the average price?",
            "Show me estates in Hong Kong",
            "What is the history of housing in HK?"
        ]

        for query in test_queries:
            print(f"\nQuery: {query}")
            result = graph.invoke({"user_query": query})
            print(f"Result: {result.get('final_response', 'No response')}")

        print("\n✅ LangGraph tests completed successfully!")

    except Exception as e:
        logger.error(f"LangGraph test failed: {e}")
        print(f"❌ LangGraph test failed: {str(e)}")

# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG Demo with LangGraph")
    parser.add_argument("--test", action="store_true", help="Run LangGraph tests instead of interactive mode")

    args = parser.parse_args()

    if args.test:
        test_langgraph()
    else:
        main()