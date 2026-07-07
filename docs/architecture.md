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
        Lambda -->|3. Escribe datos| RDS
        Lambda -.->|4. Tráfico privado| S3Endpoint[S3 Gateway Endpoint]
    end
    
    S3Endpoint -.->|Descarga imagen| S3Raw
    S3Raw -->|5. Lifecycle Rule: 7 días| Glacier[(S3 Glacier Archive)]
```

*Ver [docs/plan-de-migracion.md](file:///home/felincre/proyectos/repos/proyecto-final/docs/plan-de-migracion.md) para más detalles del plan de tiempos y Gantt.*

## Componentes

| Componente local | Equivalente cloud | Identidad / credencial |
|---|---|---|
| Contenedor LocalStack S3 | Amazon S3 | AWS IAM S3 Bucket Policy |
| Contenedor Docker Lambda | AWS Lambda | AWS IAM Role `contract-processor-role` |
| Contenedor PostgreSQL | Amazon RDS PostgreSQL | AWS Secrets Manager + VPC Security Groups |
| Docker network default | AWS VPC / Private Subnet | VPC Route Tables |
| - | S3 Gateway Endpoint | VPC Route Table entry |

## Puntos únicos de falla identificados

| SPOF | Mitigación en cloud |
|---|---|
| Caída de la base de datos RDS | Configuración de **RDS Multi-AZ** con failover automático a réplica pasiva. |
| Eliminación accidental / Ransomware en contratos | Activar **S3 Versioning** y **S3 Glacier Vault Lock** con retención legal WORM inmutable. |
| Ingesta masiva concurrente de fotos | Introducir cola AWS SQS entre el bucket S3 y la invocación de Lambda para control de tasa y reintentos. |
| Desvíos financieros o descontrol de costos | Implementar **AWS Budgets** mensuales y una **Alarma de Facturación de CloudWatch** (`EstimatedCharges`) vinculada a **Amazon SNS** para alertas proactivas. |

## Decisiones de identidad

- **Autenticación entre servicios:** La función Lambda se ejecuta con un rol de IAM específico (`contract-processor-role`) que le otorga permisos temporales mediante STS para leer del bucket de S3 y escribir logs en CloudWatch.
- **Acceso a base de datos:** El Host, Usuario y Contraseña de Postgres/RDS se inyectan en Lambda en tiempo de ejecución de forma segura desde AWS Secrets Manager usando la integración nativa con el VPC-enabled Lambda.
- **Permisos S3:** El bucket cuenta con una S3 Bucket Policy restrictiva que solo permite tráfico proveniente del VPC Endpoint asociado.




