#!/usr/bin/env python3
# Upload a mock contract to the raw S3 bucket.
# Idempotente: Sobrescribe el objeto si ya existe en S3.

import os
import sys
import json
import subprocess
import boto3

def get_tofu_output(output_name):
    try:
        iac_dir = os.path.join(os.path.dirname(__file__), "..", "iac")
        res = subprocess.run(
            ["tofu", "output", "-json", output_name],
            cwd=iac_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(res.stdout)
    except Exception as e:
        print(f"Advertencia: No se pudo obtener output '{output_name}' de OpenTofu ({e}). Usando valor por defecto.")
        # Fallback si no está inicializado
        return "contratos-serverless-raw-contracts"

def main():
    print("=== [1/3] Obteniendo nombre del bucket ===")
    bucket_name = get_tofu_output("raw_contracts_bucket_name")
    print(f"Bucket destino: {bucket_name}")

    # Crear archivo local mock si no existe
    mock_file = "mock_contract.jpg"
    print(f"=== [2/3] Preparando archivo mock local: {mock_file} ===")
    if not os.path.exists(mock_file):
        with open(mock_file, "w") as f:
            f.write("MOCK CONTRACT CONTENT FOR TESTING")
        print(f"Creado archivo local: {mock_file}")
    else:
        print(f"Archivo local existente: {mock_file}")

    print("=== [3/3] Subiendo contrato a S3 (LocalStack) ===")
    # Conectarse a LocalStack S3
    s3_client = boto3.client(
        "s3",
        endpoint_url="http://localhost:4566",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

    try:
        s3_client.upload_file(mock_file, bucket_name, mock_file)
        print(f"¡Éxito! Contrato subido a s3://{bucket_name}/{mock_file}")
    except Exception as e:
        print(f"Error al subir el contrato a S3: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
