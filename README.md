# Text-to-SQL Lambda Function

This project implements a serverless AWS Lambda function that converts natural language queries to SQL using LLM (Large Language Model) and executes them against a database.

## Features

- Natural language to SQL conversion using OpenAI GPT-4
- Secure SQL query validation
- Database connection pooling
- Error handling and logging
- OpenAPI specification
- Unit tests

## Prerequisites

- Python 3.9+
- AWS CLI configured
- PostgreSQL database
- OpenAI API key

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   ```bash
   # Database configuration
   export DB_HOST=your_db_host
   export DB_PORT=your_db_port
   export DB_NAME=your_db_name
   export DB_USER=your_db_user
   export DB_PASSWORD=your_db_password
   
   # OpenAI configuration
   export OPENAI_API_KEY=your_openai_api_key
   ```

3. Run tests:
   ```bash
   pytest tests/
   ```

## Deployment

1. Package the Lambda function:
   ```bash
   zip -r function.zip src/ requirements.txt
   ```

2. Deploy to AWS Lambda:
   ```bash
   aws lambda create-function \
     --function-name text-to-sql \
     --runtime python3.9 \
     --handler src.lambda_function.lambda_handler \
     --role your-lambda-role-arn \
     --zip-file fileb://function.zip
   ```

## API Usage

Make a POST request to the `/query` endpoint with your natural language query:

```bash
curl -X POST https://your-api-endpoint/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{"query": "Show me all orders from last month"}'
```

## Security

The function includes several security measures:
- SQL query validation to prevent unsafe operations
- Connection pooling for efficient database connections
- API key authentication
- Environment variable configuration
- Input validation and sanitization

## Architecture

The solution follows a serverless architecture:
1. API Gateway receives the HTTP request
2. Lambda function processes the request
3. OpenAI API converts natural language to SQL
4. SQL is validated for safety
5. Query is executed against the database
6. Results are returned to the client

## Best Practices

- Use connection pooling for database connections
- Implement proper error handling and logging
- Validate and sanitize all inputs
- Use environment variables for configuration
- Follow the principle of least privilege
- Implement proper authentication and authorization
- Regular security updates and patches
