import sqlite3
import time
from typing import Any, Optional, Dict
from logger import housing_logger as logger

class QueryExecutor:
    """Execute validated SQL queries safely"""

    def __init__(self, db_path: str, timeout: int = 30):
        self.db_path = db_path
        self.timeout = timeout
        self.max_rows = 1000  # Limit result size

    def execute_query(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL query with safety checks and timeout

        Args:
            sql: Validated SQL query string

        Returns:
            Execution result with data, metadata, and any errors
        """
        logger.info(f"Executing SQL query: {sql}")

        start_time = time.time()
        conn = None

        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Execute query with timeout
            cursor.execute(sql)

            # Fetch results (with limit)
            rows = cursor.fetchmany(self.max_rows)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Convert to list of dicts for easier handling
            results = [dict(row) for row in rows]

            execution_time = time.time() - start_time

            # Check if there are more rows
            has_more = cursor.fetchone() is not None

            result = {
                'success': True,
                'data': results,
                'columns': columns,
                'row_count': len(results),
                'has_more': has_more,
                'execution_time': execution_time,
                'query': sql
            }

            logger.info(f"Query executed successfully in {execution_time:.3f}s, returned {len(results)} rows")
            return result

        except sqlite3.OperationalError as e:
            error_msg = f"SQL execution error: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'operational',
                'query': sql
            }

        except sqlite3.IntegrityError as e:
            error_msg = f"Data integrity error: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'integrity',
                'query': sql
            }

        except Exception as e:
            error_msg = f"Unexpected error during query execution: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'unexpected',
                'query': sql
            }

        finally:
            if conn:
                conn.close()

    def execute_read_query(self, sql: str) -> Dict[str, Any]:
        """
        Execute SELECT queries (read-only operations)
        Additional safety checks for read operations
        """
        # Ensure it's a SELECT query
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith('SELECT'):
            return {
                'success': False,
                'error': 'Only SELECT queries are allowed in read mode',
                'error_type': 'safety',
                'query': sql
            }

        return self.execute_query(sql)

    def get_query_stats(self, sql: str) -> Dict[str, Any]:
        """
        Get execution statistics without actually executing
        Useful for query analysis and optimization
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # EXPLAIN QUERY PLAN
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            plan = cursor.fetchall()

            # Get table statistics (approximate)
            stats = {}
            for table in self._extract_tables_from_sql(sql):
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[table] = {'row_count': count}
                except:
                    stats[table] = {'row_count': 'unknown'}

            conn.close()

            return {
                'query_plan': plan,
                'table_stats': stats,
                'estimated_complexity': len(plan)  # Rough complexity metric
            }

        except Exception as e:
            logger.error(f"Error getting query stats: {e}")
            return {'error': str(e)}

    def _extract_tables_from_sql(self, sql: str) -> list:
        """Extract table names from SQL query (simple implementation)"""
        # This is a basic implementation - could be enhanced with proper SQL parsing
        tables = []

        # Look for FROM and JOIN clauses
        sql_upper = sql.upper()
        from_idx = sql_upper.find('FROM ')
        if from_idx != -1:
            from_part = sql_upper[from_idx + 5:]
            # Split by JOIN and extract table names
            parts = from_part.replace('JOIN', 'FROM').split('FROM')[1:]
            for part in parts:
                # Extract table name (simplified)
                table = part.strip().split()[0]
                if table and not table.startswith('('):  # Skip subqueries
                    tables.append(table)

        return list(set(tables))  # Remove duplicates
