# `iam/` — Políticas y Trust Documents del Proyecto

Este directorio contiene las plantillas en formato JSON de las políticas de acceso y relaciones de confianza utilizadas en el aprovisionamiento de la infraestructura:

- **`trust_policy.json`:** Define la relación de confianza (Trust Policy) para que el servicio AWS Lambda pueda asumir el rol de ejecución (`sts:AssumeRole`).
- **`lambda_policy.json`:** Política de identidad (Identity Policy) asignada al rol de la Lambda. Define el privilegio mínimo para interactuar con el Bucket S3, Secrets Manager, CloudWatch Logs y la cola SQS.
- **`bucket_policy.json`:** Política de recurso (Resource Policy) para restringir el acceso al bucket S3 únicamente a través del VPC Gateway Endpoint privado.
- **`sqs_policy.json`:** Política de recurso para la cola SQS que permite a S3 enviarle mensajes de notificación.

