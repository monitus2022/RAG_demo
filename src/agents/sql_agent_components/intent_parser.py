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
        self.schema_summary = self._get_schema_summary()
        from prompts.sql_agent_prompts import INTENT_PARSER_PROMPT
        self.prompt_template = PromptTemplate.from_template(INTENT_PARSER_PROMPT)

    def _get_schema_summary(self) -> str:
        """Get a summary of the database schema for the LLM"""
        from prompts.sql_agent_prompts import get_dynamic_schema_summary
        return get_dynamic_schema_summary()

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
                response = await chain.ainvoke({"query": query, "schema_summary": self.schema_summary})
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
