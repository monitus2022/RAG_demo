import json
import sys
import os
import asyncio
from typing import Dict, Any, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm_connector import get_llm
from logger import housing_logger as logger

class IntentParser:
    """Parse user queries into structured intent for SQL generation"""

    def __init__(self):
        self.llm = get_llm()
        self.prompt_template = PromptTemplate.from_template("""
You are an expert at analyzing housing-related questions and extracting structured information for database queries.

Given this user query about Hong Kong housing data: "{query}"

Extract the following information and return it as a valid JSON object:

{{
    "tables": ["array", "of", "table", "names", "needed"],
    "columns": ["array", "of", "column", "names", "mentioned"],
    "filters": ["array", "of", "filter", "conditions", "like", "estate_name_en = 'Lohas Park'"],
    "aggregation": "aggregation function needed (avg, sum, count, max, min, or null if none)",
    "group_by": ["array", "of", "columns", "to", "group", "by", "or", "empty", "array"],
    "order_by": ["array", "of", "columns", "to", "order", "by", "or", "empty", "array"],
    "limit": "number for LIMIT clause or null if none"
}}

Guidelines:
- Tables should be actual table names from the database schema (estates, buildings, transactions, etc.)
- Columns should be actual column names (estate_name_en, price, area, etc.)
- Filters should be in SQL-like syntax but don't include table prefixes yet
- Aggregation should be the function name in lowercase or null
- Be specific and accurate - don't guess table/column names
- If something is not mentioned, use empty arrays or null

Return only the JSON object, no additional text.
""")

    def parse(self, query: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Parse user query into structured intent with timeout

        Args:
            query: Natural language question about housing data
            timeout: Timeout in seconds for LLM call

        Returns:
            Dictionary with parsed intent or None if parsing failed
        """
        try:
            logger.info(f"Parsing intent for query: {query}")

            # Create async task with timeout
            async def _parse_async():
                # Create the chain
                chain = self.prompt_template | self.llm | StrOutputParser()

                # Invoke the chain
                response = await chain.ainvoke({"query": query})
                return response

            # Run with timeout
            response = asyncio.run(asyncio.wait_for(_parse_async(), timeout=timeout))

            logger.info(f"LLM response: {response}")

            # Parse JSON response
            intent = self._parse_json_response(response)

            if intent:
                logger.info(f"Successfully parsed intent: {intent}")
                return intent
            else:
                logger.error("Failed to parse JSON from LLM response")
                return None

        except asyncio.TimeoutError:
            logger.error(f"Intent parsing timed out after {timeout} seconds")
            return None
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            return None

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response, handling potential formatting issues"""
        try:
            # Try direct JSON parsing first
            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from response if it has extra text
            try:
                # Look for JSON object in the response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1

                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx]
                    return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        return None

# Test function
def test_intent_parser():
    """Test the intent parser with sample queries"""
    parser = IntentParser()

    test_queries = [
        "What is the average price of transactions in Lohas Park?",
        "Show me all estates in Kowloon",
        "How many buildings are in Tseung Kwan O?",
        "What are the most expensive transactions?",
        "List estates with swimming pools"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        if intent:
            print(f"Intent: {json.dumps(intent, indent=2)}")
        else:
            print("Failed to parse intent")

if __name__ == "__main__":
    test_intent_parser()