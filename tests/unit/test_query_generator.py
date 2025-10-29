import pytest
from sql_agent_components.query_generator import QueryGenerator

class TestQueryGenerator:
    """Test cases for QueryGenerator"""

    @pytest.fixture
    def generator(self):
        """Create query generator instance"""
        return QueryGenerator()

    def test_generate_simple_select_query(self, generator, sample_schema_info):
        """Test generating simple SELECT query"""
        intent = {
            'tables': ['estates'],
            'columns': ['estate_name_en'],
            'filters': [],
            'aggregation': None,
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        sql = generator.generate_query(intent, sample_schema_info)

        assert sql is not None
        assert 'SELECT' in sql.upper()
        assert 'estates' in sql
        assert 'estate_name_en' in sql

    def test_generate_aggregation_query(self, generator, sample_schema_info):
        """Test generating aggregation query"""
        intent = {
            'tables': ['transactions'],
            'columns': ['price'],
            'filters': [],
            'aggregation': 'avg',
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        sql = generator.generate_query(intent, sample_schema_info)

        assert sql is not None
        assert 'AVG(' in sql.upper()
        assert 'price' in sql

    def test_generate_join_query(self, generator, sample_schema_info):
        """Test generating JOIN query"""
        intent = {
            'tables': ['estates', 'transactions'],
            'columns': ['price'],
            'filters': [],
            'aggregation': 'avg',
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        sql = generator.generate_query(intent, sample_schema_info)

        assert sql is not None
        assert 'JOIN' in sql.upper()
        assert 'AVG(' in sql.upper()

    def test_generate_query_with_filters(self, generator, sample_schema_info):
        """Test generating query with WHERE filters"""
        intent = {
            'tables': ['estates'],
            'columns': ['estate_name_en'],
            'filters': ["district = 'Kowloon'"],
            'aggregation': None,
            'group_by': [],
            'order_by': [],
            'limit': None
        }

        sql = generator.generate_query(intent, sample_schema_info)

        assert sql is not None
        assert 'WHERE' in sql.upper()
        assert 'Kowloon' in sql

    def test_generate_query_with_limit(self, generator, sample_schema_info):
        """Test generating query with LIMIT"""
        intent = {
            'tables': ['estates'],
            'columns': ['estate_name_en'],
            'filters': [],
            'aggregation': None,
            'group_by': [],
            'order_by': [],
            'limit': 10
        }

        sql = generator.generate_query(intent, sample_schema_info)

        assert sql is not None
        assert 'LIMIT 10' in sql.upper()

    def test_generate_query_with_order_by(self, generator, sample_schema_info):
        """Test generating query with ORDER BY"""
        intent = {
            'tables': ['estates'],
            'columns': ['estate_name_en'],
            'filters': [],
            'aggregation': None,
            'group_by': [],
            'order_by': ['estate_name_en'],
            'limit': None
        }

        sql = generator.generate_query(intent, sample_schema_info)

        assert sql is not None
        assert 'ORDER BY' in sql.upper()

    def test_fix_column_mappings(self, generator, sample_schema_info):
        """Test column mapping fixes"""
        intent = {
            'tables': ['transactions'],
            'columns': ['avg_price'],  # Should map to 'price'
            'filters': [],
            'aggregation': 'avg'
        }

        fixed_intent = generator._fix_column_mappings(intent, sample_schema_info)

        assert 'price' in fixed_intent['columns']

    def test_determine_query_type_simple(self, generator):
        """Test query type determination for simple queries"""
        intent = {
            'tables': ['estates'],
            'columns': ['name'],
            'aggregation': None
        }

        query_type = generator._determine_query_type(intent)
        assert query_type == 'simple_select'

    def test_determine_query_type_aggregation(self, generator):
        """Test query type determination for aggregation queries"""
        intent = {
            'tables': ['transactions'],
            'columns': ['price'],
            'aggregation': 'avg'
        }

        query_type = generator._determine_query_type(intent)
        assert query_type == 'simple_aggregation'

    def test_determine_query_type_join_aggregation(self, generator):
        """Test query type determination for join aggregation queries"""
        intent = {
            'tables': ['estates', 'transactions'],
            'columns': ['price'],
            'aggregation': 'avg'
        }

        query_type = generator._determine_query_type(intent)
        assert query_type == 'aggregation_with_join'

    def test_select_aggregation_column(self, generator, sample_schema_info):
        """Test smart column selection for aggregations"""
        intent = {
            'tables': ['transactions'],
            'columns': ['price'],
            'aggregation': 'avg'
        }

        column = generator._select_aggregation_column(intent, sample_schema_info)
        assert column == 'price'

    def test_build_where_conditions(self, generator, sample_schema_info):
        """Test WHERE condition building"""
        filters = ["district = 'Kowloon'"]
        tables = ['estates']

        conditions = generator._build_where_conditions(filters, tables, sample_schema_info)

        assert conditions is not None
        assert 'Kowloon' in conditions

    def test_build_join_path(self, generator, sample_schema_info):
        """Test JOIN path building"""
        tables = ['estates', 'transactions']

        join_path = generator._build_join_path(tables, sample_schema_info)

        assert join_path is not None
        assert 'from_clause' in join_path
        assert 'join_clauses' in join_path