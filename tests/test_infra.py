import boto3
import pytest

LOCALSTACK_ENDPOINT = "http://localhost:4566"

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

def test_s3_bucket_exists(s3_client):
    bucket_name = "contratos-serverless-raw-contracts"
    try:
        response = s3_client.head_bucket(Bucket=bucket_name)
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    except Exception as e:
        pytest.fail(f"El bucket {bucket_name} no existe o no es accesible: {e}")

def test_s3_bucket_versioning_enabled(s3_client):
    bucket_name = "contratos-serverless-raw-contracts"
    try:
        response = s3_client.get_bucket_versioning(Bucket=bucket_name)
        assert response.get("Status") == "Enabled"
    except Exception as e:
        pytest.fail(f"No se pudo obtener el estado de versioning para el bucket {bucket_name}: {e}")

def test_lambda_function_exists(lambda_client):
    lambda_name = "contratos-serverless-contract-processor"
    try:
        response = lambda_client.get_function(FunctionName=lambda_name)
        assert response["Configuration"]["FunctionName"] == lambda_name
        assert response["Configuration"]["Runtime"] == "python3.12"
        assert response["Configuration"]["Handler"] == "contract_processor.lambda_handler"
    except Exception as e:
        pytest.fail(f"La funcion Lambda {lambda_name} no existe o fallo la validacion de configuracion: {e}")

def test_secrets_manager_secret_exists(secrets_client):
    secret_name = "contratos-serverless-db-credentials"
    try:
        response = secrets_client.describe_secret(SecretId=secret_name)
        assert response["Name"] == secret_name
    except Exception as e:
        pytest.fail(f"El secreto {secret_name} no existe o no es accesible: {e}")

@pytest.fixture(scope="module")
def sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

def test_sqs_queues_exist(sqs_client):
    try:
        # Check main queue
        response = sqs_client.get_queue_url(QueueName="contratos-serverless-contracts-queue")
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        
        # Check DLQ
        response_dlq = sqs_client.get_queue_url(QueueName="contratos-serverless-contracts-dlq")
        assert response_dlq["ResponseMetadata"]["HTTPStatusCode"] == 200
    except Exception as e:
        pytest.fail(f"Fallo al validar la existencia de las colas SQS: {e}")

def test_lambda_event_source_mapping_exists(lambda_client):
    lambda_name = "contratos-serverless-contract-processor"
    try:
        response = lambda_client.list_event_source_mappings(FunctionName=lambda_name)
        mappings = response.get("EventSourceMappings", [])
        assert len(mappings) > 0
        mapping = mappings[0]
        assert "sqs" in mapping["EventSourceArn"]
        assert mapping["State"] in ["Enabled", "Creating", "Active"]
    except Exception as e:
        pytest.fail(f"No se encontró el mapeo de eventos de SQS a Lambda: {e}")

