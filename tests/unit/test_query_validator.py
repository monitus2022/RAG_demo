import pytest
from unittest.mock import patch
from sql_agent_components.query_validator import QueryValidator

class TestQueryValidator:
    """Test cases for QueryValidator"""

    @pytest.fixture
    def validator(self, temp_db):
        """Create validator with test database"""
        return QueryValidator(temp_db)

    def test_validate_query_valid_select(self, validator):
        """Test validation of valid SELECT query"""
        sql = "SELECT estate_name_en FROM estates LIMIT 5"

        result = validator.validate_query(sql)

        assert result['valid'] is True
        assert result['safe'] is True
        assert len(result['errors']) == 0

    def test_validate_query_dangerous_drop(self, validator):
        """Test validation of dangerous DROP query"""
        sql = "DROP TABLE estates"

        result = validator.validate_query(sql)

        assert result['valid'] is False
        assert result['safe'] is False
        assert len(result['errors']) > 0
        assert 'DROP' in str(result['errors'])

    def test_validate_query_dangerous_delete(self, validator):
        """Test validation of dangerous DELETE query"""
        sql = "DELETE FROM estates WHERE 1=1"

        result = validator.validate_query(sql)

        assert result['valid'] is False
        assert result['safe'] is False
        assert len(result['errors']) > 0

    def test_validate_query_syntax_error_unbalanced_quotes(self, validator):
        """Test validation of query with unbalanced quotes"""
        sql = "SELECT * FROM estates WHERE name = 'unclosed"

        result = validator.validate_query(sql)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_query_syntax_error_unbalanced_parentheses(self, validator):
        """Test validation of query with unbalanced parentheses"""
        sql = "SELECT * FROM estates WHERE (id = 1"

        result = validator.validate_query(sql)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_query_multiple_semicolons(self, validator):
        """Test validation of query with multiple semicolons"""
        sql = "SELECT * FROM estates; SELECT * FROM transactions;"

        result = validator.validate_query(sql)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_query_no_select(self, validator):
        """Test validation of query without SELECT"""
        sql = "INSERT INTO estates VALUES (1, 'test')"

        result = validator.validate_query(sql)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_query_select_star_warning(self, validator):
        """Test validation generates warning for SELECT *"""
        sql = "SELECT * FROM estates"

        result = validator.validate_query(sql)

        assert result['valid'] is True
        assert len(result['warnings']) > 0
        assert 'SELECT *' in str(result['warnings'])

    def test_validate_query_no_where_warning(self, validator):
        """Test validation generates warning for query without WHERE"""
        sql = "SELECT estate_name_en FROM estates"

        result = validator.validate_query(sql)

        assert result['valid'] is True
        assert len(result['warnings']) > 0

    def test_validate_query_cartesian_product_warning(self, validator):
        """Test validation generates warning for potential Cartesian product"""
        sql = "SELECT e.name FROM estates e JOIN transactions t"

        result = validator.validate_query(sql)

        assert result['valid'] is True
        assert len(result['warnings']) > 0

    def test_check_dangerous_operations(self, validator):
        """Test dangerous operations detection"""
        sql = "DROP TABLE users; DELETE FROM data;"

        result = validator._check_dangerous_operations(sql)

        assert result['safe'] is False
        assert len(result['errors']) > 0

    def test_check_sql_syntax_valid(self, validator):
        """Test SQL syntax checking for valid query"""
        sql = "SELECT name FROM estates WHERE id = 1"

        result = validator._check_sql_syntax(sql)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_check_sql_syntax_invalid(self, validator):
        """Test SQL syntax checking for invalid query"""
        sql = "SELECT name FROM estates WHERE id = 'unclosed"

        result = validator._check_sql_syntax(sql)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_check_sql_injection(self, validator):
        """Test SQL injection pattern detection"""
        sql = "SELECT * FROM users WHERE id = 1; -- comment"

        result = validator._check_sql_injection(sql)

        assert result['safe'] is False
        assert len(result['errors']) > 0

    def test_check_sql_injection_script(self, validator):
        """Test script injection detection"""
        sql = "SELECT * FROM users WHERE name = '<script>alert(1)</script>'"

        result = validator._check_sql_injection(sql)

        assert result['safe'] is False
        assert len(result['errors']) > 0

    def test_check_performance(self, validator):
        """Test performance checks"""
        sql = "SELECT * FROM estates"

        result = validator._check_performance(sql)

        assert len(result['warnings']) > 0

    def test_remove_comments(self, validator):
        """Test comment removal"""
        sql = "SELECT * FROM estates -- this is a comment"

        result = validator._remove_comments(sql)

        assert '--' not in result
        assert 'SELECT * FROM estates' == result.strip()

    def test_remove_comments_multiline(self, validator):
        """Test multiline comment removal"""
        sql = "SELECT * FROM /* comment */ estates"

        result = validator._remove_comments(sql)

        assert '/*' not in result
        assert '*/' not in result

    def test_test_query_safety_safe(self, validator):
        """Test query safety testing for safe query"""
        sql = "SELECT name FROM estates"

        result = validator.test_query_safety(sql)

        assert result is True

    def test_test_query_safety_unsafe(self, validator):
        """Test query safety testing for unsafe query"""
        sql = "DROP TABLE estates"

        result = validator.test_query_safety(sql)

        assert result is False