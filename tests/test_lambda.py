import pytest
import json
from unittest.mock import patch, MagicMock
from src.lambda_function import lambda_handler, validate_sql

# Tests for the enhanced validate_sql function
@pytest.mark.parametrize("sql_query, expected", [
    # Valid queries
    ("SELECT * FROM users", True),
    ("SELECT name, email FROM customers WHERE id = 1", True),
    ("select count(*) from orders;", True),

    # Invalid queries - DML/DDL
    ("INSERT INTO users (name) VALUES ('test')", False),
    ("UPDATE users SET name = 'new' WHERE id = 1", False),
    ("DELETE FROM users WHERE id = 1", False),
    ("DROP TABLE users", False),
    ("CREATE TABLE new_users (id INT)", False),
    ("ALTER TABLE users ADD COLUMN age INT", False),
    ("TRUNCATE TABLE users", False),

    # Invalid queries - multiple statements
    ("SELECT * FROM users; SELECT * FROM products", False),
    ("SELECT * FROM users; DROP TABLE users", False),

    # Invalid queries - bypass attempts
    ("SELECT * FROM users; -- DROP TABLE users", False),
    ("/* comment */ SELECT * FROM users", True), # This is valid
    ("SELECT * FROM users WHERE name = 'a'; UPDATE users SET admin=1; --'", False),
])
def test_validate_sql_various_queries(sql_query, expected):
    assert validate_sql(sql_query) == expected

# Tests for the main lambda_handler
@patch('src.lambda_function.get_llm_response')
@patch('src.lambda_function.execute_sql')
def test_lambda_handler_success(mock_execute_sql, mock_get_llm_response):
    # Mock the LLM and DB calls
    mock_get_llm_response.return_value = "SELECT * FROM mock_table"
    mock_execute_sql.return_value = {"success": True, "data": [{"id": 1, "name": "test"}]}

    event = {
        'body': json.dumps({'query': 'show me all mocks'})
    }

    result = lambda_handler(event, None)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['sql'] == "SELECT * FROM mock_table"
    assert body['data'] == [{"id": 1, "name": "test"}]

@patch('src.lambda_function.get_llm_response')
def test_lambda_handler_unsafe_sql(mock_get_llm_response):
    # Mock the LLM to return an unsafe query
    mock_get_llm_response.return_value = "DROP TABLE users"

    event = {
        'body': json.dumps({'query': 'please drop the users table'})
    }

    result = lambda_handler(event, None)

    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert 'error' in body
    assert body['error'] == 'Invalid or unsafe SQL query generated'

@patch('src.lambda_function.get_llm_response')
@patch('src.lambda_function.execute_sql')
def test_lambda_handler_db_error(mock_execute_sql, mock_get_llm_response):
    # Mock the LLM and a failing DB call
    mock_get_llm_response.return_value = "SELECT * FROM mock_table"
    mock_execute_sql.return_value = {"success": False, "error": "DB connection failed"} # The raw error is logged, not returned

    event = {
        'body': json.dumps({'query': 'show me all mocks'})
    }

    result = lambda_handler(event, None)

    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert 'error' in body
    # Check for the generic error message
    assert body['error'] == "An internal server error occurred while executing the query."

def test_lambda_handler_bad_request():
    event = {'body': json.dumps({})}
    result = lambda_handler(event, None)
    assert result['statusCode'] == 400
    assert 'No query in request body' in json.loads(result['body'])['error']
