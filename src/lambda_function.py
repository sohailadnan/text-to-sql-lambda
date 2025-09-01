import json
import os
import logging
import boto3
from typing import Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import openai
import sqlparse
from sql_metadata import Parser

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize OpenAI client
openai.api_key = os.environ['OPENAI_API_KEY']

# Database configuration
DB_HOST = os.environ['DB_HOST']
DB_PORT = os.environ['DB_PORT']
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']

# Initialize database engine with connection pooling
engine = create_engine(
    f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True
)

def get_llm_response(prompt: str) -> str:
    """
    Get SQL query from natural language using LLM
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert SQL writer. Convert natural language to SQL queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in LLM processing: {str(e)}")
        raise

def validate_sql(sql: str) -> bool:
    """
    Validate the SQL query to ensure it is a single, read-only SELECT statement.
    """
    try:
        # Use sqlparse to parse the SQL
        parsed = sqlparse.parse(sql)

        # Filter out empty statements
        statements = [stmt for stmt in parsed if stmt.token_first(skip_ws=True)]

        if len(statements) > 1:
            logger.warning(f"Multiple SQL statements detected: {sql}")
            return False
            
        if not statements:
            return False # No statements found

        # Check the type of the single statement
        statement_type = statements[0].get_type()
        if statement_type != 'SELECT':
            logger.warning(f"Disallowed statement type '{statement_type}': {sql}")
            return False

        # As an additional security measure, check for forbidden keywords in the raw query string.
        # This helps prevent injection attempts even within comments or strings.
        sql_lower = sql.lower()
        forbidden = ['drop', 'truncate', 'delete', 'update', 'insert', 'create', 'alter']
        if any(word in sql_lower for word in forbidden):
            logger.warning(f"Forbidden keyword found in query: {sql}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error during SQL validation: {str(e)}")
        return False

def execute_sql(sql: str) -> Dict[str, Any]:
    """
    Execute SQL query and return results
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            if result.returns_rows:
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return {"success": True, "data": rows}
            return {"success": True, "data": []}
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {"success": False, "error": "An error occurred while querying the database."}

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function
    """
    try:
        # Log request
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Get the natural language query from the request
        if 'body' not in event:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No body in request'})
            }
            
        body = json.loads(event['body'])
        if 'query' not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No query in request body'})
            }
            
        natural_query = body['query']
        
        # Get SQL from LLM
        sql_query = get_llm_response(natural_query)
        
        # Validate SQL
        if not validate_sql(sql_query):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid or unsafe SQL query generated'
                })
            }
            
        # Execute SQL
        result = execute_sql(sql_query)
        
        if not result['success']:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': "An internal server error occurred while executing the query."
                })
            }
            
        # Return results
        return {
            'statusCode': 200,
            'body': json.dumps({
                'sql': sql_query,
                'data': result['data']
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': "An internal server error occurred."
            })
        }
