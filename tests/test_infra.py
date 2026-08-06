import boto3
import pytest

LOCALSTACK_ENDPOINT = "http://localhost:4566"
PROJECT_NAME = "contratos-serverless"

@pytest.fixture(scope="module")
def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

@pytest.fixture(scope="module")
def lambda_client():
    return boto3.client(
        "lambda",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

@pytest.fixture(scope="module")
def secrets_client():
    return boto3.client(
        "secretsmanager",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

@pytest.fixture(scope="module")
def sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

def test_s3_bucket_exists(s3_client):
    bucket_name = f"{PROJECT_NAME}-raw-contracts"
    response = s3_client.head_bucket(Bucket=bucket_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

def test_s3_bucket_versioning_enabled(s3_client):
    bucket_name = f"{PROJECT_NAME}-raw-contracts"
    response = s3_client.get_bucket_versioning(Bucket=bucket_name)
    assert response.get("Status") == "Enabled"

def test_lambda_function_exists(lambda_client):
    lambda_name = f"{PROJECT_NAME}-contract-processor"
    response = lambda_client.get_function(FunctionName=lambda_name)
    assert response["Configuration"]["FunctionName"] == lambda_name
    assert response["Configuration"]["Runtime"] == "python3.12"
    assert response["Configuration"]["Handler"] == "contract_processor.lambda_handler"

def test_secrets_manager_secret_exists(secrets_client):
    secret_name = f"{PROJECT_NAME}-db-credentials"
    response = secrets_client.describe_secret(SecretId=secret_name)
    assert response["Name"] == secret_name

def test_sqs_queues_exist(sqs_client):
    # Check main queue
    response = sqs_client.get_queue_url(QueueName=f"{PROJECT_NAME}-contracts-queue")
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    # Check DLQ
    response_dlq = sqs_client.get_queue_url(QueueName=f"{PROJECT_NAME}-contracts-dlq")
    assert response_dlq["ResponseMetadata"]["HTTPStatusCode"] == 200

def test_lambda_event_source_mapping_exists(lambda_client):
    lambda_name = f"{PROJECT_NAME}-contract-processor"
    response = lambda_client.list_event_source_mappings(FunctionName=lambda_name)
    mappings = response.get("EventSourceMappings", [])
    assert len(mappings) > 0
    mapping = mappings[0]
    assert "sqs" in mapping["EventSourceArn"]
    assert mapping["State"] in ["Enabled", "Creating", "Active"]

def test_s3_lifecycle_policy(s3_client):
    bucket_name = f"{PROJECT_NAME}-raw-contracts"
    response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
    rules = response.get("Rules", [])
    assert len(rules) > 0
    rule = rules[0]
    assert rule["Status"] == "Enabled"
    assert rule["ID"] == "archive-to-glacier-after-7-days"
    transitions = rule.get("Transitions", [])
    assert len(transitions) > 0
    assert transitions[0]["Days"] == 7
    assert transitions[0]["StorageClass"] == "GLACIER"

def test_lambda_vpc_configuration(lambda_client):
    lambda_name = f"{PROJECT_NAME}-contract-processor"
    response = lambda_client.get_function(FunctionName=lambda_name)
    vpc_config = response["Configuration"].get("VpcConfig", {})
    assert len(vpc_config.get("SubnetIds", [])) > 0
    assert len(vpc_config.get("SecurityGroupIds", [])) > 0

def test_lambda_env_variables(lambda_client):
    lambda_name = f"{PROJECT_NAME}-contract-processor"
    response = lambda_client.get_function(FunctionName=lambda_name)
    env_vars = response["Configuration"].get("Environment", {}).get("Variables", {})
    assert "DB_SECRET_NAME" in env_vars
    assert env_vars["DB_SECRET_NAME"] == f"{PROJECT_NAME}-db-credentials"
