# Testing Guide for LLM Agent Apps

This directory contains comprehensive tests for the HK Housing Estates Chatbot SQL Agent components.

## Test Structure

```
tests/
├── __init__.py                    # Test package initialization
├── conftest.py                    # Shared fixtures and configuration
├── unit/                         # Unit tests for individual components
│   ├── test_intent_parser.py     # IntentParser tests
│   ├── test_schema_validator.py  # SchemaValidator tests
│   ├── test_query_generator.py   # QueryGenerator tests
│   ├── test_query_validator.py   # QueryValidator tests
│   ├── test_query_executor.py    # QueryExecutor tests
│   └── test_result_formatter.py  # ResultFormatter tests
├── integration/                  # Integration tests
│   └── test_sql_pipeline.py      # Full pipeline integration tests
└── README.md                     # This file
```

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src

# Run specific test file
pytest tests/unit/test_intent_parser.py

# Run integration tests only
pytest tests/integration/

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
```

### Test Categories
```bash
# Run unit tests only
pytest -m "not integration"

# Run integration tests only
pytest -m integration

# Run tests matching pattern
pytest -k "test_parse_valid_query"
```

## Testing Strategies for LLM Agent Apps

### 1. **Mock External Dependencies**
- **LLM Calls**: Use `AsyncMock` to simulate LLM responses
- **Database**: Use in-memory SQLite with test fixtures
- **External APIs**: Mock all external service calls

### 2. **Deterministic Testing**
- Mock LLM responses to ensure consistent test results
- Use fixed test data instead of live data
- Avoid time-dependent tests

### 3. **Error Handling**
- Test timeout scenarios
- Test malformed LLM responses
- Test database connection failures
- Test invalid SQL generation

### 4. **Pipeline Integration**
- Test component interactions
- Verify error propagation
- Test data flow between components

### 5. **Performance Considerations**
- Mock expensive operations
- Use fast in-memory databases
- Avoid real network calls

## Key Testing Patterns

### LLM Response Mocking
```python
@pytest.mark.asyncio
async def test_component_with_llm(parser, mock_llm):
    mock_llm.ainvoke.return_value = '{"tables": ["estates"]}'

    result = parser.parse("test query")
    assert result is not None
```

### Database Testing
```python
def test_database_operation(executor, temp_db):
    # temp_db is an isolated test database
    result = executor.execute_query("SELECT * FROM estates")
    assert result['success'] is True
```

### Error Scenario Testing
```python
def test_error_handling(component):
    with patch.object(component, 'external_call', side_effect=Exception()):
        result = component.process()
        assert result['success'] is False
```

## Coverage Goals

- **Unit Tests**: Aim for 90%+ coverage of individual components
- **Integration Tests**: Cover critical user journeys
- **Error Paths**: Test all major error conditions

## CI/CD Integration

Tests are configured to run automatically in CI with:
- Coverage reporting (HTML and terminal)
- 80% minimum coverage requirement
- Strict test failure handling

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Descriptive Names**: Use clear, descriptive test names
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock Generously**: Mock all external dependencies
5. **Test Edge Cases**: Don't just test happy paths
6. **Fast Execution**: Keep tests running quickly

## Debugging Failed Tests

```bash
# Run with detailed output
pytest -v -s

# Run specific failing test
pytest tests/unit/test_intent_parser.py::TestIntentParser::test_parse_valid_query -v

# Debug with pdb
pytest --pdb

# Show coverage for specific file
pytest --cov=src/agents/sql_agent_components/intent_parser.py tests/unit/test_intent_parser.py