import pytest
from unittest.mock import patch
from sql_agent_components.schema_validator import SchemaValidator

class TestSchemaValidator:
    """Test cases for SchemaValidator"""

    @pytest.fixture
    def validator(self, temp_db):
        """Create validator with test database"""
        with patch('config.settings.Config.DATABASE_PATH', temp_db):
            return SchemaValidator()

    def test_validate_intent_valid(self, validator, sample_intent):
        """Test validation of valid intent"""
        result = validator.validate_intent(sample_intent)

        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert 'schema_info' in result

    def test_validate_intent_invalid_table(self, validator):
        """Test validation with non-existent table"""
        invalid_intent = {
            'tables': ['nonexistent_table'],
            'columns': ['column1'],
            'filters': [],
            'aggregation': None,
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        result = validator.validate_intent(invalid_intent)

        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert 'nonexistent_table' in str(result['errors'])

    def test_validate_intent_invalid_column(self, validator):
        """Test validation with non-existent column"""
        invalid_intent = {
            'tables': ['estates'],
            'columns': ['nonexistent_column'],
            'filters': [],
            'aggregation': None,
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        result = validator.validate_intent(invalid_intent)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_intent_invalid_aggregation(self, validator):
        """Test validation with invalid aggregation"""
        invalid_intent = {
            'tables': ['estates'],
            'columns': ['estate_name_en'],
            'filters': [],
            'aggregation': 'invalid_agg',
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        result = validator.validate_intent(invalid_intent)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_intent_invalid_limit(self, validator):
        """Test validation with invalid limit"""
        invalid_intent = {
            'tables': ['estates'],
            'columns': ['estate_name_en'],
            'filters': [],
            'aggregation': None,
            'group_by': [],
            'order_by': [],
            'limit': -1
        }

        result = validator.validate_intent(invalid_intent)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_intent_no_tables(self, validator):
        """Test validation with no tables specified"""
        invalid_intent = {
            'tables': [],
            'columns': ['column1'],
            'filters': [],
            'aggregation': None,
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        result = validator.validate_intent(invalid_intent)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_get_table_suggestions(self, validator):
        """Test table name suggestions"""
        suggestions = validator.get_table_suggestions('estat')
        assert 'estates' in suggestions

    def test_get_column_suggestions(self, validator):
        """Test column name suggestions"""
        suggestions = validator.get_column_suggestions('estates', 'name')
        assert 'estate_name_en' in suggestions

    def test_get_column_suggestions_invalid_table(self, validator):
        """Test column suggestions for non-existent table"""
        suggestions = validator.get_column_suggestions('nonexistent', 'name')
        assert suggestions == []

    def test_get_relevant_schema_info(self, validator, sample_intent):
        """Test getting relevant schema info"""
        schema_info = validator._get_relevant_schema_info(sample_intent)

        assert 'estates' in schema_info
        assert 'columns' in schema_info['estates']
        assert 'estate_name_en' in schema_info['estates']['columns']