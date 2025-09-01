import pytest
import json
from src.lambda_function import lambda_handler, validate_sql

def test_validate_sql():
    # Test valid SELECT queries
    assert validate_sql("SELECT * FROM users") == True
    assert validate_sql("SELECT id, name FROM orders WHERE date > '2023-01-01'") == True
    
    # Test invalid queries with forbidden commands
    assert validate_sql("DROP TABLE users") == False
    assert validate_sql("DELETE FROM orders") == False
    assert validate_sql("UPDATE users SET status = 'active'") == False

def test_lambda_handler_missing_body():
    event = {}
    result = lambda_handler(event, None)
    assert result['statusCode'] == 400
    assert 'error' in json.loads(result['body'])

def test_lambda_handler_missing_query():
    event = {'body': json.dumps({})}
    result = lambda_handler(event, None)
    assert result['statusCode'] == 400
    assert 'error' in json.loads(result['body'])
