import os
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    print("=== MOCK CONTRACT PROCESSOR LAMBDA ===")
    print("Received event:", json.dumps(event, indent=2))
    
    # 1. Parse S3 Event
    for record in event.get('Records', []):
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        print(f"File uploaded to S3: s3://{bucket_name}/{object_key}")
        
        # 2. Get DB Credentials from Secrets Manager (to demonstrate IAM + Secrets Manager integration)
        db_host = os.environ.get("DB_HOST", "proyecto-postgres")
        db_name = os.environ.get("DB_NAME", "contracts_db")
        db_user = os.environ.get("DB_USER", "postgres")
        
        secret_name = os.environ.get("DB_SECRET_NAME")
        if secret_name:
            print(f"Retrieving database credentials from Secrets Manager: {secret_name}")
            try:
                client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
                response = client.get_secret_value(SecretId=secret_name)
                if "SecretString" in response:
                    secret = json.loads(response["SecretString"])
                    db_host = secret.get("host", db_host)
                    db_name = secret.get("dbname", db_name)
                    db_user = secret.get("username", db_user)
                    print(f"Credentials successfully retrieved from Secrets Manager.")
            except Exception as e:
                print(f"Error fetching secret: {e}. Falling back to default/env values.")
        
        # 3. Simulate database connection and insert (to avoid psycopg2 packing issues)
        print(f"[DATABASE SIMULATION] Connecting to database at {db_host}...")
        print(f"[DATABASE SIMULATION] Running query: ")
        print(f"  INSERT INTO processed_contracts (s3_bucket, s3_key, processed_at, status)")
        print(f"  VALUES ('{bucket_name}', '{object_key}', '{datetime.utcnow().isoformat()}', 'PROCESSED');")
        print(f"[DATABASE SIMULATION] 1 row affected. Commit complete.")
        
    print("=== PROCESSING COMPLETE ===")
    return {
        "statusCode": 200,
        "body": json.dumps("Mock contract processing successful")
    }
