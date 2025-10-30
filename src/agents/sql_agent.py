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

# LangGraph-compatible function for SQL agent node using custom pipeline
def sql_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for SQL agent processing using custom component pipeline

    Args:
        state: Current graph state with user_query and other fields

    Returns:
        Updated state with sql_result
    """
    user_query = state.get("user_query", "")
    if not user_query:
        logger.warning("No user query provided to SQL agent")
        return {"sql_result": None}

    try:
        # Import components
        from sql_agent_components.intent_parser import IntentParser
        from sql_agent_components.schema_validator import SchemaValidator
        from sql_agent_components.query_generator import QueryGenerator
        from sql_agent_components.query_validator import QueryValidator
        from sql_agent_components.query_executor import QueryExecutor
        from sql_agent_components.result_formatter import ResultFormatter
        from config.settings import Config

        logger.info(f"Processing SQL query: {user_query}")

        # Step 1: Parse Intent
        intent_parser = IntentParser()
        intent = intent_parser.parse(user_query)
        if not intent:
            error_msg = "Failed to parse query intent"
            logger.error(error_msg)
            return {"sql_result": error_msg}

        # Step 2: Validate Schema
        schema_validator = SchemaValidator()
        validation_result = schema_validator.validate_intent(intent)
        if not validation_result['valid']:
            error_msg = f"Schema validation failed: {', '.join(validation_result['errors'])}"
            logger.error(error_msg)
            return {"sql_result": error_msg}

        # Step 3: Generate Query
        query_generator = QueryGenerator()
        sql_query = query_generator.generate_query(intent, validation_result['schema_info'])
        if not sql_query:
            error_msg = "Failed to generate SQL query"
            logger.error(error_msg)
            return {"sql_result": error_msg}

        # Step 4: Validate Query
        query_validator = QueryValidator(Config.DATABASE_PATH)
        query_validation = query_validator.validate_query(sql_query)
        if not query_validation['valid']:
            error_msg = f"Query validation failed: {', '.join(query_validation['errors'])}"
            logger.error(error_msg)
            return {"sql_result": error_msg}

        # Step 5: Execute Query
        query_executor = QueryExecutor(Config.DATABASE_PATH)
        execution_result = query_executor.execute_read_query(sql_query)
        if not execution_result['success']:
            error_msg = f"Query execution failed: {execution_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {"sql_result": error_msg}

        # Step 6: Format Results
        result_formatter = ResultFormatter()
        formatted_result = result_formatter.format_results(execution_result, user_query)

        final_result = formatted_result.get('display_text', 'No results to display')
        logger.info(f"SQL agent processing completed successfully")
        return {"sql_result": final_result}

    except Exception as e:
        error_msg = f"SQL agent processing failed: {str(e)}"
        logger.error(error_msg)
        return {"sql_result": error_msg}