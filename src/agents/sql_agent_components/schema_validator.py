import sqlite3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, List, Optional, Set
from config.settings import Config
from logger import housing_logger as logger

class SchemaValidator:
    """Validate that intent references valid database schema elements"""

    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.schema_cache = None
        self._load_schema()

    def _load_schema(self):
        """Load and cache database schema information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            schema = {}
            for table in tables:
                # Get table info (columns)
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]  # column names

                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table})")
                foreign_keys = cursor.fetchall()

                schema[table] = {
                    'columns': columns,
                    'foreign_keys': foreign_keys
                }

            self.schema_cache = schema
            logger.info(f"Loaded schema for {len(tables)} tables")
            conn.close()

        except Exception as e:
            logger.error(f"Failed to load database schema: {e}")
            self.schema_cache = {}

    def validate_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate intent against database schema

        Args:
            intent: Parsed intent dictionary

        Returns:
            Validation result with success flag and error messages
        """
        logger.info(f"Validating intent: {intent}")

        errors = []
        warnings = []

        # Validate tables
        tables = intent.get('tables', [])
        if not tables:
            errors.append("No tables specified in intent")
        else:
            for table in tables:
                if table not in self.schema_cache:
                    errors.append(f"Table '{table}' does not exist in database")

        # Validate columns
        columns = intent.get('columns', [])
        for column in columns:
            # Check if column exists in any of the specified tables
            found = False
            for table in tables:
                if table in self.schema_cache and column in self.schema_cache[table]['columns']:
                    found = True
                    break
            if not found:
                # Check if it's a valid column in any table (for joins)
                all_columns = set()
                for table_info in self.schema_cache.values():
                    all_columns.update(table_info['columns'])
                if column not in all_columns:
                    errors.append(f"Column '{column}' does not exist in any table")
                else:
                    warnings.append(f"Column '{column}' exists but not in specified tables - may need JOIN")

        # Validate aggregation
        aggregation = intent.get('aggregation')
        valid_aggregations = ['avg', 'sum', 'count', 'max', 'min', None]
        if aggregation and aggregation not in valid_aggregations:
            errors.append(f"Invalid aggregation function: {aggregation}")

        # Validate group_by columns
        group_by = intent.get('group_by', [])
        for column in group_by:
            if column not in columns:
                warnings.append(f"GROUP BY column '{column}' not in selected columns")

        # Validate order_by columns
        order_by = intent.get('order_by', [])
        for column in order_by:
            if column not in columns:
                warnings.append(f"ORDER BY column '{column}' not in selected columns")

        # Validate limit
        limit = intent.get('limit')
        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            errors.append(f"Invalid LIMIT value: {limit}")

        result = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'schema_info': self._get_relevant_schema_info(intent)
        }

        if result['valid']:
            logger.info("Intent validation passed")
        else:
            logger.warning(f"Intent validation failed: {errors}")

        return result

    def _get_relevant_schema_info(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Get schema information relevant to the intent"""
        tables = intent.get('tables', [])
        relevant_schema = {}

        for table in tables:
            if table in self.schema_cache:
                relevant_schema[table] = self.schema_cache[table]

        return relevant_schema

    def get_table_suggestions(self, partial_name: str) -> List[str]:
        """Get table name suggestions for partial matches"""
        return [table for table in self.schema_cache.keys()
                if partial_name.lower() in table.lower()]

    def get_column_suggestions(self, table: str, partial_name: str) -> List[str]:
        """Get column name suggestions for a table"""
        if table not in self.schema_cache:
            return []
        columns = self.schema_cache[table]['columns']
        return [col for col in columns
                if partial_name.lower() in col.lower()]
