import pytest
from sql_agent_components.result_formatter import ResultFormatter

class TestResultFormatter:
    """Test cases for ResultFormatter"""

    @pytest.fixture
    def formatter(self):
        """Create result formatter instance"""
        return ResultFormatter()

    def test_format_results_success_table(self, formatter):
        """Test formatting successful table results"""
        execution_result = {
            'success': True,
            'data': [
                {'estate_name_en': 'Lohas Park', 'district': 'Tseung Kwan O'},
                {'estate_name_en': 'Festival City', 'district': 'Kowloon'}
            ],
            'columns': ['estate_name_en', 'district'],
            'row_count': 2,
            'execution_time': 0.123,
            'has_more': False
        }

        result = formatter.format_results(execution_result, "Show me all estates")

        assert result['success'] is True
        assert result['result_type'] == 'table'
        assert 'Found 2 results:' in result['display_text']
        assert 'Lohas Park' in result['display_text']
        assert 'Festival City' in result['display_text']

    def test_format_results_success_aggregation(self, formatter):
        """Test formatting successful aggregation results"""
        execution_result = {
            'success': True,
            'data': [{'avg_price': 7795856.5375906285}],
            'columns': ['avg_price'],
            'row_count': 1,
            'execution_time': 0.813,
            'has_more': False
        }

        result = formatter.format_results(execution_result, "What is the average price?")

        assert result['success'] is True
        assert result['result_type'] == 'aggregation'
        assert 'average price' in result['display_text'].lower()
        assert 'HK$7,795,857' in result['display_text']

    def test_format_results_success_single_value(self, formatter):
        """Test formatting single value results"""
        execution_result = {
            'success': True,
            'data': [{'count': 42}],
            'columns': ['count'],
            'row_count': 1,
            'execution_time': 0.05,
            'has_more': False
        }

        result = formatter.format_results(execution_result, "How many estates are there?")

        assert result['success'] is True
        assert result['result_type'] == 'single_value'
        assert 'The result is: 42' in result['display_text']

    def test_format_results_error(self, formatter):
        """Test formatting error results"""
        execution_result = {
            'success': False,
            'error': 'Table does not exist',
            'error_type': 'operational'
        }

        result = formatter.format_results(execution_result, "Invalid query")

        assert result['success'] is False
        assert result['error_type'] == 'operational'
        assert 'couldn\'t execute your query' in result['display_text'].lower()

    def test_format_results_no_data(self, formatter):
        """Test formatting results with no data"""
        execution_result = {
            'success': True,
            'data': [],
            'columns': ['estate_name_en'],
            'row_count': 0,
            'execution_time': 0.05,
            'has_more': False
        }

        result = formatter.format_results(execution_result, "Find estates in Mars")

        assert result['success'] is True
        assert 'No results found' in result['display_text']

    def test_format_results_has_more(self, formatter):
        """Test formatting results with has_more flag"""
        execution_result = {
            'success': True,
            'data': [{'estate_name_en': 'Estate 1'}, {'estate_name_en': 'Estate 2'}],
            'columns': ['estate_name_en'],
            'row_count': 100,
            'execution_time': 0.1,
            'has_more': True
        }

        result = formatter.format_results(execution_result, "Show all estates")

        assert result['success'] is True
        assert 'more rows' in result['display_text']

    def test_is_aggregation_result_true(self, formatter):
        """Test detection of aggregation results"""
        data = [{'avg_price': 1000000}]
        columns = ['avg_price']

        result = formatter._is_aggregation_result(data, columns)

        assert result is True

    def test_is_aggregation_result_false(self, formatter):
        """Test detection of non-aggregation results"""
        data = [{'estate_name_en': 'Lohas Park'}]
        columns = ['estate_name_en']

        result = formatter._is_aggregation_result(data, columns)

        assert result is False

    def test_is_single_value_result_true(self, formatter):
        """Test detection of single value results"""
        data = [{'count': 42}]

        result = formatter._is_single_value_result(data)

        assert result is True

    def test_is_single_value_result_false(self, formatter):
        """Test detection of non-single value results"""
        data = [{'name': 'Estate', 'district': 'Area'}, {'name': 'Estate2', 'district': 'Area2'}]

        result = formatter._is_single_value_result(data)

        assert result is False

    def test_format_aggregation_result(self, formatter):
        """Test aggregation result formatting"""
        data = [{'avg_price': 7795856.5375906285}]
        columns = ['avg_price']

        result = formatter._format_aggregation_result(data, columns, "average price query")

        assert 'average price' in result['display_text'].lower()
        assert 'HK$7,795,857' in result['display_text']

    def test_format_single_value_result(self, formatter):
        """Test single value result formatting"""
        data = [{'total': 100}]
        columns = ['total']

        result = formatter._format_single_value_result(data, columns, "count query")

        assert 'The result is: 100' in result['display_text']

    def test_format_table_result(self, formatter):
        """Test table result formatting"""
        data = [{'name': 'Estate1', 'price': 1000000}]
        columns = ['name', 'price']

        result = formatter._format_table_result(data, columns, 1, 0.05, "table query")

        assert 'Found 1 results:' in result['display_text']
        assert 'Estate1' in result['display_text']
        assert 'HK$1,000,000' in result['display_text']

    def test_create_text_table(self, formatter):
        """Test text table creation"""
        data = [
            {'name': 'Estate1', 'price': 1000000},
            {'name': 'Estate2', 'price': 2000000}
        ]
        columns = ['name', 'price']

        result = formatter._create_text_table(data, columns)

        assert len(result) == 4  # Header + separator + 2 data rows
        assert 'name' in result[0]
        assert 'price' in result[0]
        assert 'Estate1' in result[2]
        assert 'HK$1,000,000' in result[2]

    def test_format_value_currency(self, formatter):
        """Test currency value formatting"""
        result = formatter._format_value(7795856.5375906285, 'price')
        assert result == 'HK$7,795,857'

    def test_format_value_integer(self, formatter):
        """Test integer value formatting"""
        result = formatter._format_value(42, 'count')
        assert result == '42'

    def test_format_value_large_number(self, formatter):
        """Test large number formatting"""
        result = formatter._format_value(1000000, 'price')
        assert result == '1,000,000'

    def test_format_value_float(self, formatter):
        """Test float value formatting"""
        result = formatter._format_value(3.14159, 'ratio')
        assert result == '3.14'

    def test_format_value_none(self, formatter):
        """Test None value formatting"""
        result = formatter._format_value(None, 'price')
        assert result == 'N/A'

    def test_get_aggregation_description_avg(self, formatter):
        """Test aggregation description for AVG"""
        result = formatter._get_aggregation_description('avg_price', 'average price query')
        assert 'average price' in result

    def test_get_aggregation_description_sum(self, formatter):
        """Test aggregation description for SUM"""
        result = formatter._get_aggregation_description('sum_amount', 'total amount query')
        assert 'total amount' in result

    def test_get_aggregation_description_count(self, formatter):
        """Test aggregation description for COUNT"""
        result = formatter._get_aggregation_description('count_items', 'count items query')
        assert 'count items' in result