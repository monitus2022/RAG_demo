import pytest
from unittest.mock import patch, AsyncMock
from sql_agent_components.intent_parser import IntentParser
from sql_agent_components.schema_validator import SchemaValidator
from sql_agent_components.query_generator import QueryGenerator
from sql_agent_components.query_validator import QueryValidator
from sql_agent_components.query_executor import QueryExecutor
from sql_agent_components.result_formatter import ResultFormatter

class TestSQLPipeline:
    """Integration tests for the complete SQL agent pipeline"""

    @pytest.fixture
    def pipeline_components(self, temp_db, mock_llm):
        """Create all pipeline components with shared fixtures"""
        with patch('llm_connector.get_llm', return_value=mock_llm), \
             patch('config.settings.Config.DATABASE_PATH', temp_db):

            intent_parser = IntentParser()
            schema_validator = SchemaValidator()
            query_generator = QueryGenerator()
            query_validator = QueryValidator(temp_db)
            query_executor = QueryExecutor(temp_db)
            result_formatter = ResultFormatter()

            return {
                'intent_parser': intent_parser,
                'schema_validator': schema_validator,
                'query_generator': query_generator,
                'query_validator': query_validator,
                'query_executor': query_executor,
                'result_formatter': result_formatter
            }

    @pytest.mark.asyncio
    async def test_full_pipeline_simple_query(self, pipeline_components, mock_llm):
        """Test complete pipeline for simple estate listing query"""
        components = pipeline_components

        # Mock LLM response for intent parsing
        mock_llm.ainvoke.return_value = '''{
            "tables": ["estates"],
            "columns": ["estate_name_en"],
            "filters": [],
            "aggregation": null,
            "group_by": [],
            "order_by": [],
            "limit": 5
        }'''

        # Step 1: Parse intent
        intent = components['intent_parser'].parse("Show me all estates")
        assert intent is not None

        # Step 2: Validate schema
        validation = components['schema_validator'].validate_intent(intent)
        assert validation['valid'] is True

        # Step 3: Generate SQL
        sql = components['query_generator'].generate_query(intent, validation['schema_info'])
        assert sql is not None
        assert 'SELECT' in sql.upper()

        # Step 4: Validate SQL
        sql_validation = components['query_validator'].validate_query(sql)
        assert sql_validation['valid'] is True

        # Step 5: Execute query
        execution_result = components['query_executor'].execute_query(sql)
        assert execution_result['success'] is True
        assert execution_result['row_count'] > 0

        # Step 6: Format results
        formatted_result = components['result_formatter'].format_results(
            execution_result, "Show me all estates"
        )
        assert formatted_result['success'] is True
        assert 'display_text' in formatted_result

    @pytest.mark.asyncio
    async def test_full_pipeline_aggregation_query(self, pipeline_components, mock_llm):
        """Test complete pipeline for aggregation query"""
        components = pipeline_components

        # Mock LLM response for aggregation intent
        mock_llm.ainvoke.return_value = '''{
            "tables": ["transactions"],
            "columns": ["price"],
            "filters": [],
            "aggregation": "avg",
            "group_by": [],
            "order_by": [],
            "limit": null
        }'''

        # Step 1: Parse intent
        intent = components['intent_parser'].parse("What is the average price?")
        assert intent is not None
        assert intent['aggregation'] == 'avg'

        # Step 2: Validate schema
        validation = components['schema_validator'].validate_intent(intent)
        assert validation['valid'] is True

        # Step 3: Generate SQL
        sql = components['query_generator'].generate_query(intent, validation['schema_info'])
        assert sql is not None
        assert 'AVG(' in sql.upper()

        # Step 4: Validate SQL
        sql_validation = components['query_validator'].validate_query(sql)
        assert sql_validation['valid'] is True

        # Step 5: Execute query
        execution_result = components['query_executor'].execute_query(sql)
        assert execution_result['success'] is True

        # Step 6: Format results
        formatted_result = components['result_formatter'].format_results(
            execution_result, "What is the average price?"
        )
        assert formatted_result['success'] is True
        assert formatted_result['result_type'] == 'aggregation'

    @pytest.mark.asyncio
    async def test_pipeline_error_handling_invalid_table(self, pipeline_components, mock_llm):
        """Test pipeline error handling for invalid table"""
        components = pipeline_components

        # Mock LLM response with invalid table
        mock_llm.ainvoke.return_value = '''{
            "tables": ["nonexistent_table"],
            "columns": ["column1"],
            "filters": [],
            "aggregation": null,
            "group_by": [],
            "order_by": [],
            "limit": null
        }'''

        # Step 1: Parse intent
        intent = components['intent_parser'].parse("Query invalid table")
        assert intent is not None

        # Step 2: Validate schema - should fail
        validation = components['schema_validator'].validate_intent(intent)
        assert validation['valid'] is False

        # Pipeline should stop here, but let's test what happens if we continue
        sql = components['query_generator'].generate_query(intent, validation['schema_info'])
        assert sql is None  # Should fail to generate SQL

    @pytest.mark.asyncio
    async def test_pipeline_error_handling_invalid_sql(self, pipeline_components, mock_llm):
        """Test pipeline error handling for invalid SQL generation"""
        components = pipeline_components

        # Mock LLM response that would generate invalid SQL
        mock_llm.ainvoke.return_value = '''{
            "tables": ["estates"],
            "columns": ["invalid_column"],
            "filters": [],
            "aggregation": null,
            "group_by": [],
            "order_by": [],
            "limit": null
        }'''

        # Step 1: Parse intent
        intent = components['intent_parser'].parse("Query with invalid column")
        assert intent is not None

        # Step 2: Validate schema - should fail due to invalid column
        validation = components['schema_validator'].validate_intent(intent)
        assert validation['valid'] is False

    def test_pipeline_query_execution_error(self, pipeline_components):
        """Test pipeline handling of query execution errors"""
        components = pipeline_components

        # Create a malformed SQL query
        sql = "SELECT * FROM nonexistent_table"

        # Step 4: Validate SQL - should pass basic validation
        sql_validation = components['query_validator'].validate_query(sql)
        assert sql_validation['valid'] is True  # Basic syntax is valid

        # Step 5: Execute query - should fail
        execution_result = components['query_executor'].execute_query(sql)
        assert execution_result['success'] is False

        # Step 6: Format error results
        formatted_result = components['result_formatter'].format_results(
            execution_result, "Query nonexistent table"
        )
        assert formatted_result['success'] is False
        assert 'error' in formatted_result

    @pytest.mark.asyncio
    async def test_pipeline_with_filters(self, pipeline_components, mock_llm):
        """Test pipeline with WHERE filters"""
        components = pipeline_components

        # Mock LLM response with filters
        mock_llm.ainvoke.return_value = '''{
            "tables": ["estates"],
            "columns": ["estate_name_en"],
            "filters": ["district = 'Kowloon'"],
            "aggregation": null,
            "group_by": [],
            "order_by": [],
            "limit": null
        }'''

        # Step 1: Parse intent
        intent = components['intent_parser'].parse("Show estates in Kowloon")
        assert intent is not None
        assert len(intent['filters']) > 0

        # Step 2: Validate schema
        validation = components['schema_validator'].validate_intent(intent)
        assert validation['valid'] is True

        # Step 3: Generate SQL
        sql = components['query_generator'].generate_query(intent, validation['schema_info'])
        assert sql is not None
        assert 'WHERE' in sql.upper()
        assert 'Kowloon' in sql

        # Step 4: Validate SQL
        sql_validation = components['query_validator'].validate_query(sql)
        assert sql_validation['valid'] is True

        # Step 5: Execute query
        execution_result = components['query_executor'].execute_query(sql)
        assert execution_result['success'] is True

        # Step 6: Format results
        formatted_result = components['result_formatter'].format_results(
            execution_result, "Show estates in Kowloon"
        )
        assert formatted_result['success'] is True

    def test_pipeline_dangerous_query_detection(self, pipeline_components):
        """Test pipeline blocks dangerous queries"""
        components = pipeline_components

        # Dangerous SQL
        sql = "DROP TABLE estates"

        # Step 4: Validate SQL - should fail
        sql_validation = components['query_validator'].validate_query(sql)
        assert sql_validation['valid'] is False
        assert sql_validation['safe'] is False

        # Should not execute dangerous queries
        assert not components['query_validator'].test_query_safety(sql)