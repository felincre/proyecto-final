# Arquitectura — Ingestador de Contratos Serverless

## Diagrama

```mermaid
graph TD
    User([Usuario / Escáner]) -->|1. Sube foto .jpg| S3Raw[S3 Bucket: raw-contracts-bucket]
    S3Raw -->|2. Evento: ObjectCreated| Lambda[AWS Lambda: contract-processor]
    
    subgraph VPC [AWS VPC]
        subgraph SubnetPrivada [Subred Privada]
            Lambda
            RDS[(RDS / PostgreSQL)]
        end
        Lambda -->|4. Escribe datos| RDS
        Lambda -.->|3. Tráfico privado| S3Endpoint[S3 Gateway Endpoint]
        Lambda -.->|5. Obtiene credenciales| SecretsMgr[(AWS Secrets Manager)]
    end
    
    S3Endpoint -.->|Descarga imagen| S3Raw
    S3Raw -->|6. Lifecycle Rule: 7 días| Glacier[(S3 Glacier Archive)]
```

*Ver [plan-de-migracion.md](plan-de-migracion.md) para más detalles del plan de tiempos y Gantt.*

## Componentes

| Componente local | Equivalente cloud | Identidad / credencial |
|---|---|---|
| Contenedor LocalStack S3 | Amazon S3 | AWS IAM S3 Bucket Policy |
| Contenedor Docker Lambda | AWS Lambda | AWS IAM Role `contract-processor-role` |
| Contenedor PostgreSQL | Amazon RDS PostgreSQL | VPC Security Groups |
| LocalStack Secrets Manager | AWS Secrets Manager | AWS KMS / Secrets Policy + IAM Role |
| Docker network default | AWS VPC / Private Subnet | VPC Route Tables |
| - | S3 Gateway Endpoint | VPC Route Table entry |

## Puntos únicos de falla identificados

| SPOF | Mitigación en cloud |
|---|---|
| Caída de la base de datos RDS | Configuración de **RDS Multi-AZ** con failover automático a réplica pasiva. |
| Eliminación accidental / Ransomware en contratos | Activar **S3 Versioning** y **S3 Glacier Vault Lock** con retención legal WORM inmutable. |
| Ingesta masiva concurrente de fotos | Introducir cola AWS SQS entre el bucket S3 y la invocación de Lambda para control de tasa y reintentos. |
| Desvíos financieros o descontrol de costos | Implementar **AWS Budgets** mensuales y una **Alarma de Facturación de CloudWatch** (`EstimatedCharges`) vinculada a **Amazon SNS** para alertas proactivas. |

## Decisiones de Identidad e Integración

- **Autenticación entre servicios:** La función Lambda se ejecuta con un rol de IAM específico (`contract-processor-role`) que le otorga permisos temporales mediante STS para leer del bucket de S3, escribir logs en CloudWatch y consultar Secrets Manager.
- **Acceso a base de datos:** El Host, Usuario y Contraseña de Postgres/RDS se inyectan en Lambda en tiempo de ejecución de forma segura desde AWS Secrets Manager, evitando credenciales hardcodeadas en variables de entorno en texto plano.
- **Permisos S3:** El bucket cuenta con una S3 Bucket Policy restrictiva que solo permite tráfico proveniente del VPC Endpoint asociado (y del administrador local de despliegue).
- **Mecanismo de Disparo (Trigger):** Se implementa una notificación directa de S3 a Lambda (`s3:ObjectCreated:*` directo a la ARN de la Lambda). Para la escala en producción, se planifica interponer una cola SQS intermedia (S3 -> SQS -> Lambda) con Dead Letter Queue (DLQ) para amortiguar picos y regular de forma asíncrona la concurrencia sobre la base de datos PostgreSQL.





