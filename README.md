# Ingesta y Procesamiento Automatizado de Contratos

Proyecto integrador del módulo Cloud Computing (ITBA).

> **Integrantes:** _completar con los miembros del grupo_

Arquitectura base: VPC + IAM + S3 + Cómputo + Base de datos, todo en LocalStack/Docker (local-first), con AWS real como referencia.

---

## Cómo arrancar

### Opción A — GitHub "Use this template" (recomendado)

1. Click en **"Use this template"** arriba a la derecha de este repo
2. Elegí nombre y dueño del repo nuevo (puede ser una organización del grupo)
3. Cloná el repo nuevo a tu máquina o abrilo en Codespaces
4. Corré `bin/init.sh "Tu Proyecto"` para personalizar README y docs
5. Listo: arrancá agregando servicios al `compose.yaml`

### Opción B — Cookiecutter / script local

Si preferís hacerlo desde la CLI sin pasar por la UI de GitHub:

```bash
# Cloná el starter
git clone https://github.com/<owner>/proyecto-final-starter.git mi-proyecto
cd mi-proyecto

# Borrá la historia del template
rm -rf .git

# Personalizá
./bin/init.sh "Mi Proyecto"

# Arrancá un repo nuevo
git init && git add . && git commit -m "init: proyecto final desde starter"

# (opcional) creá el repo en GitHub
gh repo create mi-proyecto --source=. --private --push
```

---

## Qué incluye el starter

Solo estructura — sin servicios pre-armados. Vos elegís qué levantar y dónde.

```
.
├── .devcontainer/         # Codespaces listo: postgres-client, aws-cli, docker-in-docker
├── compose.yaml           # Esqueleto vacío (services: {})
├── docs/
│   ├── architecture.md    # Plantilla con tablas vacías
│   └── decisions.md       # Formato ADR
├── iam/
│   ├── trust_policy.json  # Único molde reutilizable (EC2 assume role)
│   └── README.md
├── scripts/
│   └── README.md          # Guía de convenciones (idempotencia, no secretos)
├── iac/
│   ├── main.tf            # Donde van tus recursos
│   ├── variables.tf       # project_name, environment, region
│   ├── outputs.tf
│   └── providers/
│       ├── aws-local.tf.example     # AWS contra LocalStack
│       ├── azure-local.tf.example   # Azure contra Azurite
│       └── gcp-local.tf.example     # GCP contra emuladores
├── requirements.txt       # boto3, psycopg2, awscli-local, pytest
├── bin/init.sh            # Personaliza el starter con tu proyecto
└── .gitignore
```

Mirar `iac/README.md` para elegir provider local.

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
* **LocalStack (Ministack):** Emulando S3, Lambda, VPC, IAM y Secrets Manager en el puerto `4566`.
* **PostgreSQL:** Actuando como la base de datos relacional (RDS emulado) en el puerto `5432`.

### 2. Desplegar la infraestructura con OpenTofu (IaC)
Ejecuta el script de despliegue para inicializar OpenTofu y aplicar la configuración en LocalStack de forma automática e idempotente.
```bash
./scripts/01-deploy-infra.sh
```
Este comando aprovisionará la VPC, subredes, endpoints de S3, el bucket, las políticas y roles de IAM, el secreto de credenciales en Secrets Manager y la función Lambda.

### 3. Subir un contrato a S3 para disparar el flujo
Sube un archivo de contrato mock (`mock_contract.jpg`) a la subred S3 emulada utilizando Boto3.
```bash
python3 ./scripts/02-upload-contract.py
```
La subida del archivo `.jpg` disparará de manera automática e inmediata la ejecución de la función Lambda `contract-processor` a través de los eventos configurados en S3.

### 4. Validar el procesamiento (Logs y Base de Datos)
Verifica que el flujo se completó correctamente leyendo los logs de CloudWatch y consultando la base de datos PostgreSQL.
```bash
python3 ./scripts/03-verify-processing.py
```
Este script:
1. Conecta con la base de datos PostgreSQL y crea/consulta la tabla `processed_contracts` para validar la persistencia e idempotencia.
2. Lee los logs de ejecución reales de la función Lambda desde el log stream de CloudWatch en LocalStack, validando que el trigger de S3 se disparó de forma correcta.

### 5. Ejecutar Pruebas Unitarias
Para correr los tests unitarios y asegurar que todos los recursos locales se encuentran correctamente configurados en LocalStack, ejecuta:
```bash
pytest
```

---

## Referencias del curso

- Repo de demos por clase: [cloud-foundations-lab](https://github.com/maxflorentin/cloud-foundations-lab)
- AWS Academy Cloud Architecting (Spanish LATAM): los módulos cubren la teoría
- `cloud-foundations-lab` tiene labs 04 (IAM), 05 (EC2), 06 (S3), 07 (VPC), 08 (RDS) — usar como referencia
