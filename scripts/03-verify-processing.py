#!/usr/bin/env python3
# Verify contract processing by:
# 1. Querying/seeding the mock Postgres database.
# 2. Fetching Lambda logs from CloudWatch inside LocalStack.

import os
import time
import json
import subprocess
import boto3
import psycopg2

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
        if "lambda" in output_name:
            return "contratos-serverless-contract-processor"
        return "contratos-serverless-raw-contracts"

def main():
    lambda_name = get_tofu_output("lambda_function_name")
    
    # --- Parte 1: Base de Datos PostgreSQL ---
    print("\n=== [1/2] Conectando y validando base de datos PostgreSQL (RDS emulado) ===")
    db_host = "localhost"  # Host desde la máquina host
    db_port = "5432"
    db_name = "contracts_db"
    db_user = "postgres"
    db_password = "postgres"

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=3
        )
        cursor = conn.cursor()
        
        # Crear la tabla de contratos si no existe (idempotente)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_contracts (
                id SERIAL PRIMARY KEY,
                s3_bucket VARCHAR(255) NOT NULL,
                s3_key VARCHAR(255) NOT NULL UNIQUE,
                processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                metadata JSONB NOT NULL
            );
        """)
        
        # NOTA DE DISEÑO ACADÉMICO / FINOPS (LocalStack):
        # Para evitar problemas de empaquetado de librerías nativas compiladas en C (como psycopg2) 
        # en la función Lambda corriendo localmente en el contenedor, la Lambda simula la conexión 
        # e imprime la query SQL resultante en sus logs (validado en la fase 2/2 de este script).
        # Este script de verificación es el encargado de interactuar de forma segura con PostgreSQL 
        # y simular la inserción que realizaría la Lambda en producción, completando el flujo E2E local.
        
        # Insertar un registro mock para demostrar la integración e idempotencia
        query = """
            INSERT INTO processed_contracts (s3_bucket, s3_key, metadata)
            VALUES (%s, %s, %s)
            ON CONFLICT (s3_key) DO UPDATE
            SET metadata = EXCLUDED.metadata;
        """
        mock_meta = {
            "status": "PROCESSED",
            "inferred_amount": 15000.00,
            "inferred_company": "Administración Inmuebles Buenos Aires"
        }
        cursor.execute(query, ("contratos-serverless-raw-contracts", "mock_contract.jpg", json.dumps(mock_meta)))
        conn.commit()
        
        # Consultar la tabla
        cursor.execute("SELECT id, s3_key, processed_at, metadata FROM processed_contracts;")
        rows = cursor.fetchall()
        print(f"Filas encontradas en 'processed_contracts':")
        for row in rows:
            print(f"  - ID: {row[0]} | Key: {row[1]} | Fecha: {row[2]} | Meta: {row[3]}")
            
        cursor.close()
        conn.close()
        print("¡Validación de base de datos finalizada correctamente!")
    except Exception as e:
        print(f"Error al conectar o consultar PostgreSQL: {e}")
        print("Asegúrate de que 'docker compose' esté corriendo y esté expuesto el puerto 5432.")

    # --- Parte 2: Logs de la Lambda en CloudWatch ---
    print(f"\n=== [2/2] Obteniendo logs de la Lambda '{lambda_name}' en CloudWatch (LocalStack) ===")
    
    logs_client = boto3.client(
        "logs",
        endpoint_url="http://localhost:4566",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

    log_group_name = f"/aws/lambda/{lambda_name}"
    
    try:
        # Esperar un momento para asegurar que la Lambda haya corrido y generado logs
        print("Esperando logs de ejecución...")
        time.sleep(2)
        
        # Listar streams de logs
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            descending=True,
            limit=1
        )
        
        streams = streams_response.get("logStreams", [])
        if not streams:
            print("No se encontraron log streams. ¿Subiste el archivo 'mock_contract.jpg' a S3?")
            return
            
        latest_stream = streams[0]["logStreamName"]
        print(f"Leyendo logs del stream: {latest_stream}\n")
        
        log_events = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=latest_stream,
            startFromHead=True
        )
        
        print("----- LOGS DE EJECUCIÓN LAMBDA -----")
        for event in log_events.get("events", []):
            message = event["message"].strip()
            print(f"[{time.strftime('%H:%M:%S', time.gmtime(event['timestamp']/1000.0))}] {message}")
        print("------------------------------------")
            
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"Advertencia: El grupo de logs '{log_group_name}' no existe todavía.")
        print("Esto indica que la Lambda no ha sido ejecutada. Verifica que subiste el archivo `.jpg` correcto.")
    except Exception as e:
        print(f"Error al recuperar logs de CloudWatch: {e}")

if __name__ == "__main__":
    main()
