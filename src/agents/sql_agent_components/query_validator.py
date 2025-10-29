import re
import sqlite3
from typing import Dict, Any, Optional, List
from logger import housing_logger as logger

class QueryValidator:
    """Validate generated SQL queries for syntax and safety"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.dangerous_keywords = {
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'MERGE', 'BULK'
        }

    def validate_query(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL query for syntax and safety

        Args:
            sql: SQL query string to validate

        Returns:
            Validation result with success flag and error messages
        """
        logger.info(f"Validating SQL query: {sql}")

        errors = []
        warnings = []

        # Check for dangerous operations
        dangerous_check = self._check_dangerous_operations(sql)
        if not dangerous_check['safe']:
            errors.extend(dangerous_check['errors'])

        # Check SQL syntax
        syntax_check = self._check_sql_syntax(sql)
        if not syntax_check['valid']:
            errors.extend(syntax_check['errors'])

        # Check for SQL injection patterns
        injection_check = self._check_sql_injection(sql)
        if not injection_check['safe']:
            errors.extend(injection_check['errors'])

        # Performance checks
        performance_check = self._check_performance(sql)
        warnings.extend(performance_check['warnings'])

        result = {
            'valid': len(errors) == 0,
            'safe': len([e for e in errors if 'dangerous' in e.lower()]) == 0,
            'errors': errors,
            'warnings': warnings
        }

        if result['valid']:
            logger.info("SQL query validation passed")
        else:
            logger.warning(f"SQL query validation failed: {errors}")

        return result

    def _check_dangerous_operations(self, sql: str) -> Dict[str, Any]:
        """Check for dangerous SQL operations"""
        sql_upper = sql.upper()
        errors = []

        for keyword in self.dangerous_keywords:
            if re.search(r'\b' + keyword + r'\b', sql_upper):
                errors.append(f"Dangerous operation detected: {keyword}")

        return {
            'safe': len(errors) == 0,
            'errors': errors
        }

    def _check_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """Check basic SQL syntax"""
        errors = []

        # Remove comments for validation
        sql = self._remove_comments(sql)

        # Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            errors.append("Unbalanced parentheses")

        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            errors.append("Unbalanced single quotes")

        double_quotes = sql.count('"') - sql.count('\\"')
        if double_quotes % 2 != 0:
            errors.append("Unbalanced double quotes")

        # Check for required SELECT keyword
        if not sql.upper().strip().startswith('SELECT'):
            errors.append("Query must start with SELECT")

        # Check for semicolons (shouldn't have multiple)
        semicolon_count = sql.count(';')
        if semicolon_count > 1:
            errors.append("Multiple semicolons detected")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def _check_sql_injection(self, sql: str) -> Dict[str, Any]:
        """Check for potential SQL injection patterns"""
        errors = []

        # Check for suspicious patterns
        suspicious_patterns = [
            r';\s*--',  # Semicolon followed by comment
            r';\s*/\*',  # Semicolon followed by block comment
            r'union\s+select.*--',  # Union select with comment
            r'/\*.*\*/.*select',  # Block comment before select
        ]

        sql_lower = sql.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, sql_lower, re.IGNORECASE):
                errors.append(f"Potential SQL injection pattern detected: {pattern}")

        # Check for script tags or other injection vectors
        if '<script' in sql_lower or 'javascript:' in sql_lower:
            errors.append("Script injection attempt detected")

        return {
            'safe': len(errors) == 0,
            'errors': errors
        }

    def _check_performance(self, sql: str) -> Dict[str, Any]:
        """Check for potential performance issues"""
        warnings = []

        sql_upper = sql.upper()

        # Check for SELECT *
        if 'SELECT *' in sql_upper and 'FROM' in sql_upper:
            warnings.append("SELECT * detected - consider specifying columns")

        # Check for missing WHERE clause on large tables
        if 'FROM' in sql_upper and 'WHERE' not in sql_upper:
            warnings.append("Query without WHERE clause may be slow on large tables")

        # Check for Cartesian products (JOIN without ON)
        join_count = sql_upper.count('JOIN')
        on_count = sql_upper.count(' ON ')
        if join_count > 0 and on_count < join_count:
            warnings.append("Potential Cartesian product - missing JOIN conditions")

        return {'warnings': warnings}

    def _remove_comments(self, sql: str) -> str:
        """Remove SQL comments for validation"""
        # Remove single-line comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        # Remove multi-line comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        return sql

    def test_query_safety(self, sql: str) -> bool:
        """
        Test if query can be executed safely (without actually executing)

        Returns True if safe to execute
        """
        validation = self.validate_query(sql)
        return validation['valid'] and validation['safe']
