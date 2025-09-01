# Environment variables file creation
$envContent = @"
OPENAI_API_KEY=your-openai-api-key
DB_HOST=your-database-host
DB_PORT=5432
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
"@
Set-Content -Path ".env" -Value $envContent

# Create deployment package directory
New-Item -ItemType Directory -Force -Path .\package
Copy-Item -Path .\src\lambda_function.py -Destination .\package\
Copy-Item -Path .\requirements.txt -Destination .\package\

# Install dependencies
Set-Location .\package
python -m pip install -r requirements.txt -t .

# Create deployment ZIP
Compress-Archive -Path * -DestinationPath ..\function.zip -Force
Set-Location ..

# AWS CLI commands for deployment
$functionName = "text-to-sql-function"
$role = "text-to-sql-lambda-role"

# Create IAM role for Lambda
aws iam create-role --role-name $role `
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            }
        }]
    }'

# Attach basic Lambda execution policy
aws iam attach-role-policy --role-name $role `
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create Lambda function
aws lambda create-function `
    --function-name $functionName `
    --runtime python3.9 `
    --handler lambda_function.lambda_handler `
    --role (aws iam get-role --role-name $role --query 'Role.Arn' --output text) `
    --zip-file fileb://function.zip `
    --timeout 30 `
    --memory-size 256 `
    --environment Variables="{
        OPENAI_API_KEY=$env:OPENAI_API_KEY,
        DB_HOST=$env:DB_HOST,
        DB_PORT=$env:DB_PORT,
        DB_NAME=$env:DB_NAME,
        DB_USER=$env:DB_USER,
        DB_PASSWORD=$env:DB_PASSWORD
    }"

# Create API Gateway
$apiName = "text-to-sql-api"
aws apigateway import-rest-api --body file://openapi.yaml --name $apiName

# Deploy the API
$apiId = (aws apigateway get-rest-apis --query "items[?name=='$apiName'].id" --output text)
aws apigateway create-deployment --rest-api-id $apiId --stage-name prod
