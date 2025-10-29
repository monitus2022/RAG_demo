import pytest
from unittest.mock import patch, AsyncMock
import json
from sql_agent_components.intent_parser import IntentParser

class TestIntentParser:
    """Test cases for IntentParser"""

    @pytest.fixture
    def parser(self, mock_llm):
        """Create parser with mocked LLM"""
        with patch('llm_connector.get_llm', return_value=mock_llm):
            return IntentParser()

    @pytest.mark.asyncio
    async def test_parse_valid_query(self, parser, mock_llm):
        """Test parsing a valid query"""
        mock_response = '{"tables": ["estates"], "columns": ["estate_name_en"], "filters": []}'
        mock_llm.ainvoke.return_value = mock_response

        result = parser.parse("What estates are available?")

        assert result is not None
        assert result['tables'] == ['estates']
        assert result['columns'] == ['estate_name_en']
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_invalid_json(self, parser, mock_llm):
        """Test handling of invalid JSON response"""
        mock_llm.ainvoke.return_value = "invalid json response"

        result = parser.parse("test query")

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_with_json_embedded(self, parser, mock_llm):
        """Test parsing JSON embedded in text"""
        mock_response = 'Here is the result: {"tables": ["transactions"], "columns": ["price"]}'
        mock_llm.ainvoke.return_value = mock_response

        result = parser.parse("What are the prices?")

        assert result is not None
        assert result['tables'] == ['transactions']
        assert result['columns'] == ['price']

    @pytest.mark.asyncio
    async def test_parse_timeout(self, parser, mock_llm):
        """Test timeout handling"""
        import asyncio
        mock_llm.ainvoke.side_effect = asyncio.TimeoutError()

        result = parser.parse("test query", timeout=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_with_aggregation(self, parser, mock_llm):
        """Test parsing query with aggregation"""
        mock_response = '''{
            "tables": ["transactions"],
            "columns": ["price"],
            "aggregation": "avg",
            "filters": []
        }'''
        mock_llm.ainvoke.return_value = mock_response

        result = parser.parse("What is the average price?")

        assert result is not None
        assert result['aggregation'] == 'avg'
        assert result['columns'] == ['price']

    def test_parse_json_response_valid(self, parser):
        """Test JSON parsing with valid JSON"""
        response = '{"tables": ["estates"], "columns": ["name"]}'
        result = parser._parse_json_response(response)

        assert result == {"tables": ["estates"], "columns": ["name"]}

    def test_parse_json_response_invalid(self, parser):
        """Test JSON parsing with invalid JSON"""
        response = "not json"
        result = parser._parse_json_response(response)

        assert result is None

    def test_parse_json_response_embedded(self, parser):
        """Test JSON parsing with JSON embedded in text"""
        response = 'Some text {"tables": ["test"]} more text'
        result = parser._parse_json_response(response)

        assert result == {"tables": ["test"]}