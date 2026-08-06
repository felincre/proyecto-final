# Ingesta y Procesamiento Automatizado de Contratos

Proyecto integrador del módulo Cloud Computing (ITBA).

> **Integrantes:** Felipe Indalecio Crespo

## Problema

Una empresa gestiona un volumen creciente de contratos en formato físico y digital. Hoy, extraer los datos relevantes de cada contrato (montos, fechas, firmantes, condiciones) requiere que un operador lea el documento completo de forma manual, lo que resulta lento, propenso a errores y difícil de escalar.

Se necesita una solución que permita digitalizar los contratos (escaneándolos como imagen), subirlos a la nube y obtener automáticamente los datos estructurados que el negocio ya sabe que necesita, sin intervención humana en el procesamiento.

## Solución

Arquitectura serverless orientada a eventos que automatiza el pipeline de ingesta: al subir una imagen de contrato a un bucket de S3, una cola SQS amortigua el evento y dispara una función Lambda que extrae los metadatos y los persiste en una base de datos relacional (PostgreSQL/RDS). Todo emulado localmente con LocalStack y Docker Compose.

---

## Estructura del Proyecto

Este repositorio contiene la implementación completa de la arquitectura y la lógica de procesamiento:

```
.
├── compose.yaml           # Servicios locales: LocalStack (S3, SQS, Lambda, Secrets Manager) y PostgreSQL (RDS)
├── assets/                # Archivos mock y assets locales del proyecto
│   └── mock_contract.jpg  # Imagen de contrato mock de prueba
├── iac/                   # Infraestructura como Código (IaC) en OpenTofu (Terraform)
│   ├── main.tf            # Declaración de todos los recursos (VPC, colas SQS, lambda, bucket S3, secretos)
│   ├── variables.tf       # Variables de configuración del proyecto (región, ambiente, etc.)
│   ├── outputs.tf         # Outputs de la infraestructura
│   └── aws-local.tf       # Proveedor de AWS configurado para apuntar a LocalStack local
├── src/
│   └── contract_processor.py # Código Python de la Lambda que parsea mensajes SQS e ingresa datos a Postgres
├── scripts/
│   ├── 01-deploy-infra.sh    # Script automatizado para desplegar la IaC en LocalStack
│   ├── 02-upload-contract.py # Script de demostración para subir un contrato mock a S3
│   └── 03-verify-processing.py # Script de validación de base de datos y obtención de logs de CloudWatch
├── tests/
│   └── test_infra.py      # Pruebas unitarias automatizadas usando pytest y boto3
├── docs/                  # Documentación de arquitectura, decisiones y resiliencia
│   ├── architecture.md    # Diagrama de arquitectura y descripción detallada de componentes
│   ├── decisions.md       # Decisiones de arquitectura documentadas (ADR)
│   ├── plan-de-migracion.md # Plan de migración física a AWS
│   ├── resilience-proyecto.md # Plan de resiliencia, alta disponibilidad, RTO/RPO y DR
│   └── estimacion-costos.md # Estimación de costos y tradeoffs FinOps (desarrollo vs producción)
├── iam/                   # Plantillas JSON de referencia (trust, lambda, bucket, SQS policies)
└── requirements.txt       # Dependencias de Python (.venv)
```

---

## Checklist del proyecto

Al final del módulo, este repo debería tener:

- [x] `docs/architecture.md` con tu diagrama y componentes
- [x] `docs/decisions.md` con al menos 5 decisiones documentadas (ADR)
- [x] `iam/` con los JSON de tu solución (trust + policies + bucket policy)
- [x] `scripts/` con al menos 3 demos automatizados (idempotentes)
- [x] `compose.yaml` con los servicios que tu arquitectura usa
- [x] Tests unitarios (`pytest` pasa)
- [x] README explicando cómo correrlo end-to-end

---

## Cómo correr el proyecto localmente (Local-first)

Para levantar la infraestructura y ejecutar el flujo completo en tu entorno de desarrollo local, sigue estos pasos:

### 1. Iniciar los contenedores Docker (LocalStack & PostgreSQL)
Levanta los servicios definidos en el archivo compose.
```bash
docker compose up -d
```
Esto iniciará:
* **LocalStack (Ministack):** Emulando S3, SQS, SNS, Lambda, VPC, IAM y Secrets Manager en el puerto `4566`.
* **PostgreSQL:** Actuando como la base de datos relacional (RDS emulado) en el puerto `5432`.

### 1.5 Instalar dependencias de Python
```bash
pip install -r requirements.txt
```

### 2. Desplegar la infraestructura con OpenTofu (IaC)
Ejecuta el script de despliegue para inicializar OpenTofu y aplicar la configuración en LocalStack de forma automática e idempotente.
```bash
./scripts/01-deploy-infra.sh
```
Este comando aprovisionará la VPC, subredes, endpoints de S3, el bucket, las colas SQS (principal y DLQ), el Event Source Mapping, las políticas y roles de IAM, el secreto de credenciales en Secrets Manager y la función Lambda.

### 3. Subir un contrato a S3 para disparar el flujo
Sube un archivo de contrato mock (`assets/mock_contract.jpg`) a la subred S3 emulada utilizando Boto3.
```bash
python3 ./scripts/02-upload-contract.py
```
La subida del archivo `.jpg` disparará una notificación de S3 hacia la cola SQS `contratos-serverless-contracts-queue`. La cola procesará el evento y activará de manera automática e indirecta (desacoplada) la ejecución de la función Lambda `contratos-serverless-contract-processor`.

### 4. Validar el procesamiento (Logs y Base de Datos)
Verifica que el flujo se completó correctamente leyendo los logs de CloudWatch y consultando la base de datos PostgreSQL.
```bash
python3 ./scripts/03-verify-processing.py
```
Este script:
1. Conecta con la base de datos PostgreSQL y crea/consulta la tabla `processed_contracts` para validar la persistencia e idempotencia.
2. Lee los logs de ejecución reales de la función Lambda desde el log stream de CloudWatch en LocalStack, validando que la Lambda se haya disparado mediante el evento encolado de SQS (`Processing event received from SQS queue...`).

### 5. Ejecutar Pruebas Unitarias
Para correr los tests unitarios y asegurar que todos los recursos locales se encuentran correctamente configurados en LocalStack (incluyendo las colas SQS y los mapeos de eventos), ejecuta:
```bash
pytest
```


---

## Referencias del curso

- Repo de demos por clase: [cloud-foundations-lab](https://github.com/maxflorentin/cloud-foundations-lab)
- AWS Academy Cloud Architecting (Spanish LATAM): los módulos cubren la teoría
- `cloud-foundations-lab` tiene labs 04 (IAM), 05 (EC2), 06 (S3), 07 (VPC), 08 (RDS) — usar como referencia
