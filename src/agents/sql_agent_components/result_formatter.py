import json
from typing import Dict, Any, List, Optional
from logger import housing_logger as logger

class ResultFormatter:
    """Format SQL query results for user consumption"""

    def __init__(self):
        self.max_display_rows = 10
        self.currency_fields = ['price', 'avg_price', 'net_ft_price', 'avg_ft_price', 'avg_net_ft_price',
                               'unit_price', 'total_price', 'avg_transaction_price']

    def format_results(self, execution_result: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """
        Format execution results into user-friendly output

        Args:
            execution_result: Result from QueryExecutor
            original_query: Original user query for context

        Returns:
            Formatted result with human-readable output
        """
        logger.info(f"Formatting results for query: {original_query}")

        if not execution_result.get('success', False):
            return self._format_error_result(execution_result, original_query)

        # Format successful results
        data = execution_result.get('data', [])
        columns = execution_result.get('columns', [])
        row_count = execution_result.get('row_count', 0)
        execution_time = execution_result.get('execution_time', 0)

        # Determine result type and format accordingly
        if self._is_aggregation_result(data, columns):
            formatted = self._format_aggregation_result(data, columns, original_query)
        elif self._is_single_value_result(data):
            formatted = self._format_single_value_result(data, columns, original_query)
        else:
            formatted = self._format_table_result(data, columns, row_count, execution_time, original_query)

        # Add metadata
        formatted.update({
            'query': original_query,
            'execution_time': f"{execution_time:.3f}s",
            'total_rows': row_count,
            'has_more': execution_result.get('has_more', False)
        })

        logger.info(f"Results formatted successfully: {len(formatted.get('display_text', ''))} chars")
        return formatted

    def _format_error_result(self, execution_result: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """Format error results"""
        error_msg = execution_result.get('error', 'Unknown error')
        error_type = execution_result.get('error_type', 'unknown')

        return {
            'success': False,
            'error_type': error_type,
            'display_text': f"❌ Sorry, I couldn't execute your query: {error_msg}",
            'technical_details': {
                'error': error_msg,
                'query': original_query,
                'error_type': error_type
            }
        }

    def _is_aggregation_result(self, data: List[Dict], columns: List[str]) -> bool:
        """Check if result is from an aggregation query"""
        if not data or not columns:
            return False

        # Check for aggregation column names
        agg_indicators = ['avg', 'sum', 'count', 'min', 'max', 'total']
        return any(any(indicator in col.lower() for indicator in agg_indicators) for col in columns)

    def _is_single_value_result(self, data: List[Dict]) -> bool:
        """Check if result contains a single value"""
        return len(data) == 1 and len(data[0]) == 1

    def _format_aggregation_result(self, data: List[Dict], columns: List[str], original_query: str) -> Dict[str, Any]:
        """Format aggregation results (averages, sums, etc.)"""
        if not data:
            return {'display_text': "No data found for your query."}

        row = data[0]

        # Format based on the type of aggregation
        formatted_parts = []

        for col, value in row.items():
            if value is not None:
                formatted_value = self._format_value(value, col)
                # Create human-readable description
                description = self._get_aggregation_description(col, original_query)
                formatted_parts.append(f"{description}: {formatted_value}")

        display_text = " ".join(formatted_parts)

        return {
            'result_type': 'aggregation',
            'display_text': display_text,
            'raw_data': data,
            'formatted_values': {col: self._format_value(row.get(col), col) for col in columns}
        }

    def _format_single_value_result(self, data: List[Dict], columns: List[str], original_query: str) -> Dict[str, Any]:
        """Format single value results"""
        value = data[0][columns[0]] if data and columns else None
        formatted_value = self._format_value(value, columns[0] if columns else '')

        return {
            'result_type': 'single_value',
            'display_text': f"The result is: {formatted_value}",
            'raw_data': data,
            'formatted_value': formatted_value
        }

    def _format_table_result(self, data: List[Dict], columns: List[str], row_count: int,
                           execution_time: float, original_query: str) -> Dict[str, Any]:
        """Format tabular results"""
        if not data:
            return {'display_text': "No results found for your query."}

        # Limit display rows
        display_data = data[:self.max_display_rows]
        has_more = len(data) > self.max_display_rows

        # Create table representation
        table_lines = []
        table_lines.append(f"Found {row_count} results:")

        # Simple text table
        if len(display_data) <= 5:  # Show full table for small results
            table_lines.extend(self._create_text_table(display_data, columns))
        else:
            # Show summary for larger results
            table_lines.append(f"Showing first {len(display_data)} rows:")
            table_lines.extend(self._create_text_table(display_data, columns))

        if has_more:
            table_lines.append(f"... and {row_count - self.max_display_rows} more rows")

        return {
            'result_type': 'table',
            'display_text': "\n".join(table_lines),
            'raw_data': data,
            'display_rows': len(display_data),
            'has_more_display': has_more
        }

    def _create_text_table(self, data: List[Dict], columns: List[str]) -> List[str]:
        """Create a simple text-based table"""
        if not data or not columns:
            return []

        lines = []

        # Header
        header = " | ".join(str(col) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for row in data:
            formatted_row = []
            for col in columns:
                value = row.get(col, '')
                formatted_value = self._format_value(value, col)
                formatted_row.append(str(formatted_value))
            lines.append(" | ".join(formatted_row))

        return lines

    def _format_value(self, value: Any, column_name: str) -> str:
        """Format individual values based on type and column"""
        if value is None:
            return "N/A"

        # Format currency values
        if any(curr in column_name.lower() for curr in self.currency_fields):
            try:
                # Assume HKD for housing prices
                if isinstance(value, (int, float)):
                    return f"HK${value:,.0f}"
            except (ValueError, TypeError):
                pass

        # Format floats
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            else:
                return f"{value:.2f}"

        # Format large numbers
        if isinstance(value, int) and abs(value) > 1000:
            return f"{value:,}"

        return str(value)

    def _get_aggregation_description(self, column: str, original_query: str) -> str:
        """Generate human-readable description for aggregation results"""
        column_lower = column.lower()

        # Extract aggregation type
        if 'avg' in column_lower:
            agg_type = "average"
        elif 'sum' in column_lower:
            agg_type = "total"
        elif 'count' in column_lower:
            agg_type = "count"
        elif 'min' in column_lower:
            agg_type = "minimum"
        elif 'max' in column_lower:
            agg_type = "maximum"
        else:
            agg_type = "result"

        # Extract field name (remove aggregation prefix)
        field_name = column_lower
        for prefix in ['avg_', 'sum_', 'count_', 'min_', 'max_', 'total_']:
            if field_name.startswith(prefix):
                field_name = field_name[len(prefix):]
                break

        # Human-readable field names
        field_aliases = {
            'price': 'price',
            'transaction_price': 'transaction price',
            'net_ft_price': 'net price per sq ft',
            'avg_ft_price': 'average price per sq ft'
        }

        field_desc = field_aliases.get(field_name, field_name.replace('_', ' '))

        return f"The {agg_type} {field_desc}"
