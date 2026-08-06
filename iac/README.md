# `iac/` — Infrastructure as Code (IaC)

Toda la infraestructura de red, seguridad, mensajería y cómputo está definida como código utilizando OpenTofu (Terraform).

## Componentes Declarados (`main.tf`)

El archivo [main.tf](main.tf) define e interconecta los siguientes recursos de nube:
1. **Red (VPC):** VPC base, subredes privadas, tablas de ruteo asociadas y un **VPC Gateway Endpoint** para enrutar el tráfico de S3 internamente sin salir a Internet.
2. **Seguridad (IAM & Security Groups):** 
   * `aws_iam_role` de ejecución para la Lambda.
   * `aws_iam_policy` que otorga permisos limitados de lectura en S3, obtención de secretos en Secrets Manager, y recepción/borrado de mensajes en SQS.
   * `aws_security_group` para controlar el tráfico entrante/saliente de la Lambda.
3. **Almacenamiento (S3):** Bucket de ingesta de contratos con versionado activado (`aws_s3_bucket_versioning`) y regla de ciclo de vida para transicionar objetos a Glacier a los 7 días.
4. **Mensajería (SQS & DLQ):**
   * Cola principal `contracts_queue` para almacenar los eventos de subida de S3.
   * Cola de descarte `contracts_dlq` para aislar fallos recurrentes (redrive policy con 3 intentos máximos).
   * Política de cola `aws_sqs_queue_policy` que autoriza a S3 a enviar mensajes a la cola.
5. **Cómputo & Desencadenadores:**
   * Función Lambda `contract_processor`.
   * `aws_s3_bucket_notification` configurada para enviar eventos `.jpg` a SQS.
   * `aws_lambda_event_source_mapping` que conecta SQS como disparador de la Lambda.
6. **Configuraciones (Secrets Manager):**
   * Secreto `db_credentials` y su versión para inyectar credenciales del motor de base de datos Postgres de forma cifrada y dinámica.

---

## Cómo Ejecutar y Modificar la IaC

### Proveedor Local (LocalStack)
El proveedor está configurado en el archivo [aws-local.tf](aws-local.tf), el cual redirige todas las llamadas de la API de AWS hacia el endpoint emulado en `http://localhost:4566`.

### Comandos Útiles

Siempre ejecuta los comandos de OpenTofu desde el directorio de infraestructura:
```bash
cd iac
```

1. **Inicializar OpenTofu** (descarga proveedores y módulos):
   ```bash
   tofu init
   ```
2. **Validar sintaxis y configuración**:
   ```bash
   tofu validate
   ```
3. **Planificar cambios** (muestra qué se creará, modificará o destruirá):
   ```bash
   tofu plan
   ```
4. **Aplicar la configuración** (desplegar en LocalStack):
   ```bash
   tofu apply
   ```

## Convenciones del Repositorio

- **Idempotencia:** La infraestructura se puede destruir y crear limpiamente en un solo comando sin dejar recursos huérfanos.
- **Exclusión de Estado:** Los archivos temporales y locales de estado de Terraform (`.tfstate`, `.tfstate.backup` y la carpeta `.terraform/`) están explícitamente ignorados en `.gitignore` para seguridad y limpieza del control de versiones.
- **Portabilidad:** Se eliminaron todas las rutas absolutas locales en variables y configuraciones, haciendo que el repositorio sea 100% portable para cualquier operador.

