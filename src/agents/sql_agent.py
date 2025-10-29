import sqlite3
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities.sql_database import SQLDatabase
from llm_connector import get_llm
from config.settings import Config
from logger import housing_logger as logger

class SQLAgentCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to log SQL agent thought process"""

    def on_agent_action(self, action, **kwargs):
        """Log when agent takes an action"""
        logger.info(f"SQL Agent Action: {action.tool} - {action.tool_input}")

    def on_agent_finish(self, finish, **kwargs):
        """Log when agent finishes"""
        logger.info(f"SQL Agent Finish: {finish.return_values}")

    def on_tool_start(self, serialized, input_str, **kwargs):
        """Log when a tool starts"""
        logger.info(f"SQL Tool Start: {serialized['name']} - {input_str}")

    def on_tool_end(self, output, **kwargs):
        """Log when a tool ends"""
        logger.info(f"SQL Tool End: {output}")

    def on_tool_error(self, error, **kwargs):
        """Log tool errors"""
        logger.error(f"SQL Tool Error: {error}")

class SQLAgent:
    """SQL Agent for querying housing estate data from SQLite database"""

    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.llm = get_llm()
        self.db = None
        self.agent = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the SQL database and agent"""
        try:
            # Create SQLDatabase instance
            self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")

            # Create custom callback handler for logging
            callback_handler = SQLAgentCallbackHandler()

            # Create SQL agent with LangChain
            self.agent = create_sql_agent(
                llm=self.llm,
                db=self.db,
                verbose=True,
                handle_parsing_errors=True,
                callbacks=[callback_handler]
            )

            logger.info("SQL Agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SQL Agent: {e}")
            raise

    def query(self, user_query: str) -> Optional[str]:
        """
        Execute a natural language query against the housing database

        Args:
            user_query: Natural language question about housing data

        Returns:
            Query result as formatted string, or None if failed
        """
        try:
            if not self.agent:
                logger.error("SQL Agent not initialized")
                return None

            # Execute the query
            result = self.agent.invoke({"input": user_query})

            # Extract the final answer
            final_answer = result.get("output", "")

            logger.info(f"SQL Query executed successfully: {user_query[:50]}...")
            return final_answer

        except Exception as e:
            logger.error(f"SQL query failed: {e}")
            return f"Error executing SQL query: {str(e)}"

    def get_table_info(self) -> str:
        """Get information about available tables and their schemas"""
        try:
            if not self.db:
                return "Database not initialized"

            tables = self.db.get_table_names()
            table_info = []

            for table in tables:
                info = self.db.get_table_info([table])
                table_info.append(str(info))

            return "\n\n".join(table_info)

        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return f"Error getting table information: {str(e)}"

# Global SQL agent instance
sql_agent = None

def get_sql_agent() -> SQLAgent:
    """Get or create the global SQL agent instance"""
    global sql_agent
    if sql_agent is None:
        sql_agent = SQLAgent()
    return sql_agent

# LangGraph-compatible function for SQL agent node
def sql_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for SQL agent processing

    Args:
        state: Current graph state with user_query and other fields

    Returns:
        Updated state with sql_result
    """
    user_query = state.get("user_query", "")
    if not user_query:
        logger.warning("No user query provided to SQL agent")
        return {"sql_result": None}

    agent = get_sql_agent()
    result = agent.query(user_query)

    return {"sql_result": result}