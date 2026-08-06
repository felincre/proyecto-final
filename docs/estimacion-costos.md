# Estimación de Costos (FinOps) — Ingesta y Procesamiento de Contratos

Este documento detalla el análisis de costos para el entorno de desarrollo y la proyección para producción del proyecto integrador, siguiendo las buenas prácticas de FinOps y optimización de arquitectura.

---

## 1. Contexto de Negocio
La solución responde a la necesidad de extraer datos y metadatos estructurados de contratos escaneados de forma rápida, segura y serverless, reduciendo el tiempo de procesamiento manual y los errores operativos. 

*   **Presupuesto dev mensual objetivo:** USD 15.00
*   **Presupuesto prod mensual objetivo:** USD 100.00
*   **Región de despliegue:** us-east-1

---

## 2. Entorno de Desarrollo (Dev / Local-First)

En desarrollo se prioriza el costo mínimo para el baseline de pruebas. Al utilizar una arquitectura serverless basada en eventos (S3 ➔ SQS ➔ Lambda), los servicios de cómputo y mensajería operan enteramente dentro del **AWS Free Tier**.

### Estructura de Costos Estimada (Dev)
| Servicio AWS | Tipo | Uso Mensual | Precio Unitario | Costo Mensual (USD) | Notas / Justificación |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Amazon RDS PostgreSQL** | `db` | 730 hs | $0.017 / hs | $12.41 | db.t3.micro (Single-AZ). Es el baseline fijo más costoso. |
| **AWS Secrets Manager** | `security` | 1 secreto | $0.40 / secret | $0.40 | Credenciales de la base de datos PostgreSQL. |
| **Amazon S3 (Standard)** | `storage` | 10 GB | $0.023 / GB | $0.23 | Bucket `raw-contracts` para almacenamiento inmediato. |
| **Amazon S3 Glacier** | `storage` | 50 GB | $0.0036 / GB | $0.18 | Archivo histórico (Glacier Flexible Retrieval) tras 7 días. |
| **AWS Lambda** | `compute` | 1,000 ejec. | $0.00 | $0.00 | Procesador de contratos (128MB, 2s/run). Cubierto por Free Tier. |
| **Amazon SQS** | `network` | 1,000 msgs. | $0.00 | $0.00 | Cola principal y DLQ. Cubierto por Free Tier. |
| **VPC S3 Endpoint** | `network` | 730 hs | $0.00 | $0.00 | Tipo **Gateway** para tráfico interno a S3 (gratuito). |
| **Data Transfer Out** | `network` | 5 GB | $0.00 | $0.00 | Egress a Internet. Cubierto por Free Tier (primeros 100GB/mes). |

*   **Costo Mensual Dev Total:** **USD 13.22**
*   **Cumplimiento del Budget:** Sí, con un **12% de margen libre** (USD 1.78 restante).

---

## 3. Entorno de Producción (Escalado)

Para producción, el sistema debe garantizar alta disponibilidad (VPC Multi-AZ), tolerancia a fallos, y soportar un volumen escalado de **100,000 contratos al mes** (tráfico 100x mayor) y retención histórica de 1 TB.

### Estructura de Costos Proyectada (Prod)
| Servicio AWS | Tipo | Uso Mensual | Precio Unitario | Costo Mensual (USD) | Notas / Justificación |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Amazon RDS PostgreSQL** | `db` | 730 hs | $0.034 / hs | $24.82 | db.t3.micro (**Multi-AZ** para replicación síncrona y alta disponibilidad). |
| **Application Load Balancer** | `network` | 730 hs | $0.0305 / hs | $22.27 | ALB para balancear tráfico de APIs con 1 LCU promedio ($0.0225/hs + $0.008/hs). |
| **Data Transfer Out** | `network` | 500 GB | $0.09 / GB | $36.00 | Egress a Internet (primeros 100GB gratis, 400GB facturables). |
| **Amazon S3 (Standard)** | `storage` | 200 GB | $0.023 / GB | $4.60 | Almacenamiento inicial antes de transición a Glacier. |
| **Amazon S3 Glacier** | `storage` | 1,000 GB (1 TB)| $0.0036 / GB | $3.68 | Historial masivo de contratos bajo Glacier Flexible Retrieval. |
| **AWS Secrets Manager** | `security` | 1 secreto | $0.40 / secret | $0.40 | Almacenamiento de credenciales productivas. |
| **AWS Lambda (ARM64)** | `compute` | 100,000 ejec. | $0.0000133/GB-s | $0.35 | 100k invocaciones (128MB, 2s/run = 25,000 GB-s). |
| **Amazon SQS** | `network` | 100,000 msgs. | $0.40 / 1M req. | $0.04 | Tráfico de cola amortiguando picos de subida de contratos. |
| **VPC S3 Endpoint** | `network` | 730 hs | $0.00 | $0.00 | Tipo Gateway para tráficos internos eficientes y gratuitos. |

*   **Costo Mensual Prod Total:** **USD 92.16**
*   **Cumplimiento del Budget:** Sí, entra en el presupuesto de USD 100.00 con un **8% de margen** (USD 7.84 de holgura).

---

## 4. Decisiones Clave de Diseño y Tradeoffs

1.  **VPC S3 Endpoint vs. NAT Gateway (Ahorro de ~USD 32/mes):**
    El NAT Gateway es indispensable para que las Lambdas privadas tengan acceso a Internet general, pero cuesta USD 32.85/mes fijos. Dado que el flujo de nuestra aplicación Lambda se comunica únicamente de forma interna (S3, SQS y Secrets Manager), reemplazamos la necesidad de un NAT Gateway con un **VPC Endpoint de tipo Gateway para S3** (completamente gratuito) y comunicación local.
    *   *Tradeoff:* Si la Lambda requiriera en el futuro llamar a APIs externas de OCR (como Google Cloud Vision o Azure Cognitive Services), este diseño privado fallaría y requeriría habilitar un NAT Gateway o usar VPC Endpoint Interface de costo fijo (~$7.3/mes).
2.  **Transición Agresiva de Ciclo de Vida en S3 (Ahorro del 84% de storage):**
    Mantener 1 TB de contratos en S3 Standard costaría USD 23.00/mes. Al transicionar los contratos automáticamente a **Glacier Flexible Retrieval** a los 7 días, el costo se reduce a USD 3.60/mes.
    *   *Tradeoff:* Si los usuarios necesitan descargar o visualizar contratos históricos frecuentemente, el tiempo de recuperación de Glacier (de 3 a 5 horas) afectaría la experiencia de usuario. En caso de requerir acceso inmediato, se debería evaluar S3 Glacier Instant Retrieval ($0.004/GB).
3.  **Encendido Bajo Demanda de RDS en Desarrollo:**
    En producción, RDS debe estar encendido 24/7 (USD 24.82). Para un entorno de desarrollo que solo opera 10 horas al día de lunes a viernes, apagar la base de datos dev reduce las horas mensuales de 730 a 220, bajando el costo de RDS dev de USD 12.41 a **USD 3.74/mes**, liberando un presupuesto considerable.
