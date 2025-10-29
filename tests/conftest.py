import pytest
import sqlite3
import tempfile
import os
from unittest.mock import MagicMock, AsyncMock
from langchain_core.prompts import PromptTemplate

@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm

@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing"""
    # Create temporary file for database
    db_fd, db_path = tempfile.mkstemp()

    # Create test schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create test tables
    cursor.execute('''
        CREATE TABLE estates (
            estate_id INTEGER PRIMARY KEY,
            estate_name_en TEXT,
            district TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE transactions (
            transaction_id INTEGER PRIMARY KEY,
            unit_id INTEGER,
            price REAL,
            transaction_date DATE
        )
    ''')

    cursor.execute('''
        CREATE TABLE buildings (
            building_id INTEGER PRIMARY KEY,
            estate_id INTEGER,
            building_name TEXT,
            FOREIGN KEY (estate_id) REFERENCES estates (estate_id)
        )
    ''')

    # Insert test data
    cursor.execute("INSERT INTO estates VALUES (1, 'Lohas Park', ' Tseung Kwan O')")
    cursor.execute("INSERT INTO estates VALUES (2, 'Festival City', 'Kowloon')")
    cursor.execute("INSERT INTO transactions VALUES (1, 1, 5000000.0, '2023-01-01')")
    cursor.execute("INSERT INTO transactions VALUES (2, 2, 6000000.0, '2023-02-01')")

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def sample_intent():
    """Sample intent for testing"""
    return {
        'tables': ['estates'],
        'columns': ['estate_name_en'],
        'filters': [],
        'aggregation': None,
        'group_by': [],
        'order_by': [],
        'limit': None
    }

@pytest.fixture
def sample_schema_info():
    """Sample schema information for testing"""
    return {
        'estates': {
            'columns': ['estate_id', 'estate_name_en', 'district'],
            'foreign_keys': []
        },
        'transactions': {
            'columns': ['transaction_id', 'unit_id', 'price', 'transaction_date'],
            'foreign_keys': []
        }
    }

@pytest.fixture
def mock_prompt_template():
    """Mock prompt template"""
    template = MagicMock(spec=PromptTemplate)
    template.from_template = MagicMock(return_value=template)
    return template