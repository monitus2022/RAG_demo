import pytest
from unittest.mock import patch
from sql_agent_components.query_executor import QueryExecutor

class TestQueryExecutor:
    """Test cases for QueryExecutor"""

    @pytest.fixture
    def executor(self, temp_db):
        """Create executor with test database"""
        return QueryExecutor(temp_db)

    def test_execute_query_success(self, executor):
        """Test successful query execution"""
        sql = "SELECT estate_name_en FROM estates LIMIT 1"

        result = executor.execute_query(sql)

        assert result['success'] is True
        assert result['row_count'] == 1
        assert 'estate_name_en' in result['columns']
        assert len(result['data']) == 1
        assert result['data'][0]['estate_name_en'] == 'Lohas Park'

    def test_execute_query_select_star(self, executor):
        """Test SELECT * query execution"""
        sql = "SELECT * FROM estates LIMIT 1"

        result = executor.execute_query(sql)

        assert result['success'] is True
        assert result['row_count'] == 1
        assert len(result['columns']) > 1

    def test_execute_query_with_limit(self, executor):
        """Test query execution with LIMIT"""
        sql = "SELECT estate_name_en FROM estates LIMIT 2"

        result = executor.execute_query(sql)

        assert result['success'] is True
        assert result['row_count'] == 2

    def test_execute_query_no_results(self, executor):
        """Test query execution with no results"""
        sql = "SELECT estate_name_en FROM estates WHERE estate_id = 999"

        result = executor.execute_query(sql)

        assert result['success'] is True
        assert result['row_count'] == 0
        assert len(result['data']) == 0

    def test_execute_query_aggregation(self, executor):
        """Test aggregation query execution"""
        sql = "SELECT COUNT(*) as count FROM estates"

        result = executor.execute_query(sql)

        assert result['success'] is True
        assert result['row_count'] == 1
        assert result['data'][0]['count'] == 2

    def test_execute_query_join(self, executor):
        """Test JOIN query execution"""
        sql = """
        SELECT e.estate_name_en, t.price
        FROM estates e
        LEFT JOIN transactions t ON e.estate_id = t.unit_id
        LIMIT 2
        """

        result = executor.execute_query(sql)

        assert result['success'] is True
        assert result['row_count'] == 2

    def test_execute_read_query_success(self, executor):
        """Test read-only query execution"""
        sql = "SELECT estate_name_en FROM estates"

        result = executor.execute_read_query(sql)

        assert result['success'] is True
        assert result['row_count'] == 2

    def test_execute_read_query_non_select(self, executor):
        """Test read-only query rejects non-SELECT"""
        sql = "INSERT INTO estates VALUES (3, 'Test Estate', 'Test District')"

        result = executor.execute_read_query(sql)

        assert result['success'] is False
        assert 'Only SELECT queries' in result['error']

    def test_get_query_stats(self, executor):
        """Test query statistics generation"""
        sql = "SELECT estate_name_en FROM estates WHERE estate_id = 1"

        result = executor.get_query_stats(sql)

        assert 'query_plan' in result
        assert 'table_stats' in result
        assert 'estimated_complexity' in result

    def test_get_query_stats_invalid_sql(self, executor):
        """Test query stats with invalid SQL"""
        sql = "INVALID SQL QUERY"

        result = executor.get_query_stats(sql)

        assert 'error' in result

    def test_extract_tables_from_sql_simple(self, executor):
        """Test table extraction from simple SQL"""
        sql = "SELECT * FROM estates"

        tables = executor._extract_tables_from_sql(sql)

        assert 'estates' in tables

    def test_extract_tables_from_sql_join(self, executor):
        """Test table extraction from JOIN SQL"""
        sql = "SELECT * FROM estates e JOIN transactions t ON e.id = t.id"

        tables = executor._extract_tables_from_sql(sql)

        assert 'estates' in tables
        assert 'transactions' in tables

    def test_extract_tables_from_sql_complex(self, executor):
        """Test table extraction from complex SQL"""
        sql = """
        SELECT e.name, AVG(t.price)
        FROM estates e
        JOIN buildings b ON e.estate_id = b.estate_id
        JOIN transactions t ON b.building_id = t.unit_id
        GROUP BY e.name
        """

        tables = executor._extract_tables_from_sql(sql)

        assert 'estates' in tables
        assert 'buildings' in tables
        assert 'transactions' in tables

    def test_execute_query_operational_error(self, executor):
        """Test handling of operational errors"""
        sql = "SELECT * FROM nonexistent_table"

        result = executor.execute_query(sql)

        assert result['success'] is False
        assert result['error_type'] == 'operational'
        assert 'error' in result

    def test_execute_query_integrity_error(self, executor):
        """Test handling of integrity errors"""
        # This would require a constraint violation, but for testing we'll mock it
        with patch.object(executor, '_execute_query_with_connection') as mock_exec:
            from sqlite3 import IntegrityError
            mock_exec.side_effect = IntegrityError("Constraint violation")

            sql = "INSERT INTO estates VALUES (1, 'duplicate', 'district')"
            result = executor.execute_query(sql)

            assert result['success'] is False
            assert result['error_type'] == 'integrity'

    def test_execute_query_unexpected_error(self, executor):
        """Test handling of unexpected errors"""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = Exception("Unexpected error")

            sql = "SELECT * FROM estates"
            result = executor.execute_query(sql)

            assert result['success'] is False
            assert result['error_type'] == 'unexpected'