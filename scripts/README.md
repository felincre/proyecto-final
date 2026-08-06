# `scripts/` — Demos Automatizados del Proyecto

Este directorio contiene los scripts que orquestan el despliegue, la simulación y la validación del pipeline:

- **`01-deploy-infra.sh`:** Inicializa OpenTofu y aplica los recursos declarados de forma automatizada e idempotente en LocalStack.
- **`02-upload-contract.py`:** Sube una imagen mock (`assets/mock_contract.jpg`) a S3 utilizando la librería `boto3`. Esto inicia de manera automática la cadena de eventos: `S3 ObjectCreated -> SQS Queue -> Lambda event mapping`.
- **`03-verify-processing.py`:**
  1. Conecta con el contenedor local PostgreSQL para verificar la persistencia de los metadatos transaccionales.
  2. Consulta la API de CloudWatch Logs en LocalStack para recuperar la bitácora de ejecución de la Lambda y corroborar el parsing del payload proveniente de SQS.

## Convenciones Implementadas

* **Idempotencia:** Todos los scripts son seguros de ejecutar múltiples veces de forma consecutiva.
* **Sin Secretos:** No existen contraseñas, claves o IDs quemados en el código. Las credenciales se inyectan dinámicamente.
* **Auto-documentados:** Cada ejecución imprime de forma estructurada los pasos realizados y los resultados obtenidos.

