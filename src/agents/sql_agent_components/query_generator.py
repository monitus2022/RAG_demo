import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, Optional, List
from logger import housing_logger as logger

class QueryGenerator:
    """Generate SQL queries from validated intent and schema information"""

    def __init__(self):
        self.templates = self._load_query_templates()

    def _load_query_templates(self) -> Dict[str, str]:
        """Load SQL query templates for different patterns"""
        return {
            'simple_select': "SELECT {columns} FROM {table}",
            'aggregation': "SELECT {aggregation}({column}) AS {alias} FROM {table}",
            'join_two_tables': "SELECT {select_clause} FROM {table1} t1 JOIN {table2} t2 ON {join_condition}",
            'filtered': "{base_query} WHERE {filters}",
            'grouped': "{base_query} GROUP BY {group_by}",
            'ordered': "{base_query} ORDER BY {order_by}",
            'limited': "{base_query} LIMIT {limit}"
        }

    def generate_query(self, intent: Dict[str, Any], schema_info: Dict[str, Any]) -> Optional[str]:
        """
        Generate SQL query from intent and schema information

        Args:
            intent: Validated intent dictionary
            schema_info: Schema information from validator

        Returns:
            Generated SQL query string or None if generation fails
        """
        try:
            logger.info(f"Generating query for intent: {intent}")

            # First, try to fix any column mapping issues
            fixed_intent = self._fix_column_mappings(intent, schema_info)
            logger.info(f"Fixed intent: {fixed_intent}")

            # Determine query type and structure
            query_type = self._determine_query_type(fixed_intent)

            if query_type == 'aggregation_with_join':
                sql = self._generate_aggregation_join_query(fixed_intent, schema_info)
            elif query_type == 'simple_aggregation':
                sql = self._generate_simple_aggregation_query(fixed_intent, schema_info)
            else:
                sql = self._generate_simple_select_query(fixed_intent, schema_info)

            if sql:
                logger.info(f"Generated SQL: {sql}")
                return sql
            else:
                logger.error("Failed to generate SQL query")
                return None

        except Exception as e:
            logger.error(f"Error generating query: {e}")
            return None

    def _fix_column_mappings(self, intent: Dict[str, Any], schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Fix column mappings in intent to use actual schema columns"""
        fixed_intent = intent.copy()
        columns = intent.get('columns', [])

        # Map semantic column names to actual schema columns
        semantic_mapping = {
            'price': 'price',
            'avg_price': 'price',
            'average_price': 'price',
            'transaction_price': 'price',
            'sale_price': 'price',
            'market_price': 'avg_ft_price',  # from estate_monthly_market_info
            'net_price': 'avg_net_ft_price',  # from estate_monthly_market_info
            'rent_price': 'avg_ft_rent',  # from estate_monthly_market_info
            'net_rent_price': 'avg_net_ft_rent',  # from estate_monthly_market_info
            'avg_net_ft_price': 'price',  # LLM sometimes suggests this
        }

        fixed_columns = []
        for col in columns:
            # Try semantic mapping first
            mapped_col = semantic_mapping.get(col.lower().replace(' ', '_'))
            if mapped_col and self._column_exists_in_tables(mapped_col, intent.get('tables', []), schema_info):
                fixed_columns.append(mapped_col)
                logger.info(f"Mapped column '{col}' to '{mapped_col}'")
            elif self._column_exists_in_tables(col, intent.get('tables', []), schema_info):
                # Column exists as-is
                fixed_columns.append(col)
            else:
                # Column doesn't exist, try to find a similar one
                fallback_col = self._find_fallback_column(col, intent.get('tables', []), schema_info)
                if fallback_col:
                    fixed_columns.append(fallback_col)
                    logger.info(f"Replaced invalid column '{col}' with fallback '{fallback_col}'")
                else:
                    logger.warning(f"Could not find valid column for '{col}', keeping as-is")
                    fixed_columns.append(col)

        fixed_intent['columns'] = fixed_columns
        return fixed_intent

    def _find_fallback_column(self, invalid_col: str, tables: List[str], schema_info: Dict[str, Any]) -> Optional[str]:
        """Find a fallback column when the suggested column doesn't exist"""
        # Common fallbacks for price-related queries
        if 'price' in invalid_col.lower():
            # Look for any price-related column in the tables
            price_candidates = ['price', 'avg_ft_price', 'avg_net_ft_price', 'unit_price']
            for candidate in price_candidates:
                if self._column_exists_in_tables(candidate, tables, schema_info):
                    return candidate

        # For other cases, try partial matching
        for table in tables:
            if table in schema_info:
                for col in schema_info[table]['columns']:
                    if invalid_col.lower() in col.lower() or col.lower() in invalid_col.lower():
                        return col

        return None

    def _determine_query_type(self, intent: Dict[str, Any]) -> str:
        """Determine the type of query needed"""
        tables = intent.get('tables', [])
        aggregation = intent.get('aggregation')
        filters = intent.get('filters', [])

        if aggregation and len(tables) > 1:
            return 'aggregation_with_join'
        elif aggregation:
            return 'simple_aggregation'
        else:
            return 'simple_select'

    def _generate_aggregation_join_query(self, intent: Dict[str, Any], schema_info: Dict[str, Any]) -> Optional[str]:
        """Generate aggregation query with JOINs"""
        tables = intent.get('tables', [])
        if len(tables) < 2:
            return None

        aggregation = intent.get('aggregation', 'avg')

        # Smart column selection for aggregations
        column = self._select_aggregation_column(intent, schema_info)
        if not column:
            logger.error(f"Could not determine aggregation column from {intent.get('columns', [])}")
            return None

        # Determine target table for the column
        target_table = self._find_column_table(column, tables, schema_info)
        if not target_table:
            logger.error(f"Could not find table containing column '{column}'")
            return None

        # Build JOIN path
        join_path = self._build_join_path(tables, schema_info)
        if not join_path:
            logger.error("Could not determine JOIN path between tables")
            return None

        # Construct the query - use table alias instead of full table name
        table_alias = self._get_table_alias(target_table, tables)
        select_clause = f"{aggregation.upper()}({table_alias}.{column}) AS {aggregation}_{column}"

        from_clause = join_path['from_clause']
        join_clauses = join_path['join_clauses']

        sql = f"SELECT {select_clause} FROM {from_clause}"
        if join_clauses:
            sql += f" {' '.join(join_clauses)}"

        # Add WHERE clause for filters
        filters = intent.get('filters', [])
        if filters:
            where_conditions = self._build_where_conditions(filters, tables, schema_info)
            if where_conditions:
                sql += f" WHERE {where_conditions}"

        logger.info(f"Generated aggregation JOIN query: {sql}")
        return sql

    def _select_aggregation_column(self, intent: Dict[str, Any], schema_info: Dict[str, Any]) -> Optional[str]:
        """Smart column selection for aggregations based on context"""
        columns = intent.get('columns', [])
        tables = intent.get('tables', [])

        # Map semantic column names to actual schema columns
        semantic_mapping = {
            'price': 'price',
            'avg_price': 'price',
            'average_price': 'price',
            'transaction_price': 'price',
            'sale_price': 'price',
            'market_price': 'avg_ft_price',  # from estate_monthly_market_info
            'net_price': 'avg_net_ft_price',  # from estate_monthly_market_info
            'rent_price': 'avg_ft_rent',  # from estate_monthly_market_info
            'net_rent_price': 'avg_net_ft_rent',  # from estate_monthly_market_info
        }

        # First, try semantic mapping
        for col in columns:
            mapped_col = semantic_mapping.get(col.lower().replace(' ', '_'))
            if mapped_col:
                # Verify the mapped column exists in the appropriate table
                if self._column_exists_in_tables(mapped_col, tables, schema_info):
                    return mapped_col

        # Fallback: find any valid column in the specified tables
        for col in columns:
            if self._column_exists_in_tables(col, tables, schema_info):
                return col

        # Last resort: look for common price columns
        price_columns = ['price', 'avg_ft_price', 'avg_net_ft_price', 'unit_price']
        for price_col in price_columns:
            if self._column_exists_in_tables(price_col, tables, schema_info):
                return price_col

        return None

    def _find_column_table(self, column: str, tables: List[str], schema_info: Dict[str, Any]) -> Optional[str]:
        """Find which table contains the specified column"""
        for table in tables:
            if table in schema_info and column in schema_info[table]['columns']:
                return table
        return None

    def _get_table_alias(self, table_name: str, tables: List[str]) -> str:
        """Get the table alias for a given table name"""
        # Simple alias mapping - could be enhanced
        aliases = {
            'estates': 'e',
            'buildings': 'b',
            'units': 'u',
            'transactions': 't',
            'estate_school_nets': 'esn',
            'estate_mtr_lines': 'eml',
            'estate_facilities': 'ef',
            'facilities': 'f',
            'districts': 'd',
            'subregions': 'sr',
            'regions': 'r',
            'phases': 'p',
            'estate_monthly_market_info': 'emmi'
        }
        return aliases.get(table_name, table_name[0])  # Fallback to first letter

    def _column_exists_in_tables(self, column: str, tables: List[str], schema_info: Dict[str, Any]) -> bool:
        """Check if column exists in any of the specified tables"""
        return self._find_column_table(column, tables, schema_info) is not None

    def _generate_simple_aggregation_query(self, intent: Dict[str, Any], schema_info: Dict[str, Any]) -> Optional[str]:
        """Generate simple aggregation query"""
        table = intent.get('tables', [None])[0]
        if not table or table not in schema_info:
            return None

        aggregation = intent.get('aggregation', 'avg')
        column = intent.get('columns', [None])[0]
        if not column or column not in schema_info[table]['columns']:
            return None

        sql = f"SELECT {aggregation.upper()}({column}) AS {aggregation}_{column} FROM {table}"

        # Add filters
        filters = intent.get('filters', [])
        if filters:
            where_conditions = self._build_where_conditions(filters, [table], schema_info)
            if where_conditions:
                sql += f" WHERE {where_conditions}"

        return sql

    def _generate_simple_select_query(self, intent: Dict[str, Any], schema_info: Dict[str, Any]) -> Optional[str]:
        """Generate simple SELECT query"""
        table = intent.get('tables', [None])[0]
        if not table or table not in schema_info:
            return None

        columns = intent.get('columns', ['*'])
        if columns == ['*']:
            select_clause = '*'
        else:
            select_clause = ', '.join(columns)

        sql = f"SELECT {select_clause} FROM {table}"

        # Add filters
        filters = intent.get('filters', [])
        if filters:
            where_conditions = self._build_where_conditions(filters, [table], schema_info)
            if where_conditions:
                sql += f" WHERE {where_conditions}"

        # Add ORDER BY
        order_by = intent.get('order_by', [])
        if order_by:
            sql += f" ORDER BY {', '.join(order_by)}"

        # Add LIMIT
        limit = intent.get('limit')
        if limit:
            sql += f" LIMIT {limit}"

        return sql

    def _build_join_path(self, tables: List[str], schema_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build JOIN path between tables using foreign key relationships"""
        # For now, implement a simple approach for estates -> buildings -> units -> transactions
        # This is specific to our housing database schema

        if 'estates' in tables and 'transactions' in tables:
            return {
                'from_clause': 'estates e',
                'join_clauses': [
                    'JOIN buildings b ON e.estate_id = b.estate_id',
                    'JOIN units u ON b.building_id = u.building_id',
                    'JOIN transactions t ON u.unit_id = t.unit_id'
                ]
            }

        # Add more JOIN patterns as needed
        return None

    def _build_where_conditions(self, filters: List[str], tables: List[str], schema_info: Dict[str, Any]) -> Optional[str]:
        """Build WHERE conditions from filters"""
        if not filters:
            return None

        conditions = []
        for filter_str in filters:
            # Parse filter like "estate_name_en = 'Lohas Park'"
            match = re.match(r'(\w+)\s*=\s*(.+)', filter_str)
            if match:
                column, value = match.groups()
                # Find which table contains this column
                for table in tables:
                    if table in schema_info and column in schema_info[table]['columns']:
                        # Use table alias if we have JOINs
                        if len(tables) > 1 and table == 'estates':
                            conditions.append(f"e.{column} = {value}")
                        elif len(tables) > 1 and table == 'transactions':
                            conditions.append(f"t.{column} = {value}")
                        else:
                            conditions.append(f"{table}.{column} = {value}")
                        break

        return ' AND '.join(conditions) if conditions else None
