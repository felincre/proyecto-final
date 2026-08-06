# Estimación de Costos (FinOps) — Ingesta y Procesamiento de Contratos

Este documento detalla el análisis de costos para el entorno de desarrollo y la proyección para producción del proyecto integrador, adaptado al modelo de negocio de una **plataforma SaaS de gestión de alquileres** (donde propietarios y administradores digitalizan y automatizan la extracción de datos de sus contratos).

---

## 1. Contexto de Negocio
La aplicación está orientada a administradores de propiedades que necesitan extraer rápidamente datos clave de los contratos de alquiler (montos, nombres de inquilinos, fechas de vigencia y penalidades) sin necesidad de leer manualmente las páginas completas del documento.

*   **Presupuesto dev mensual objetivo:** USD 15.00
*   **Presupuesto prod mensual objetivo:** USD 55.00
*   **Región de despliegue:** us-east-1

---

## 2. Entorno de Desarrollo (Dev / Local-First)

En desarrollo se asume una escala pequeña de pruebas académicas e integración: **10 contratos procesados al mes** (cada uno de aproximadamente 2 MB). El cómputo y la mensajería operan enteramente dentro del **AWS Free Tier**.

### Estructura de Costos Estimada (Dev)
| Servicio AWS | Tipo | Uso Mensual | Precio Unitario | Costo Mensual (USD) | Notas / Justificación |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Amazon RDS PostgreSQL** | `db` | 730 hs | $0.017 / hs | $12.41 | db.t3.micro (Single-AZ). Servidor de base de datos encendido 24/7. |
| **AWS Secrets Manager** | `security` | 1 secreto | $0.40 / secret | $0.40 | Credenciales seguras de la base de datos relacional. |
| **Amazon S3 (Standard)** | `storage` | 0.5 GB | $0.023 / GB | $0.01 | Bucket temporal `raw-contracts` para subidas iniciales. |
| **Amazon S3 Glacier** | `storage` | 5 GB | $0.0036 / GB | $0.02 | Almacenamiento histórico de respaldo (Glacier Flexible Retrieval). |
| **AWS Lambda** | `compute` | 10 ejec. | $0.00 | $0.00 | Procesador OCR de contratos. Cubierto por Free Tier. |
| **Amazon SQS** | `network` | 10 msgs. | $0.00 | $0.00 | Cola principal y DLQ. Cubierto por Free Tier. |
| **VPC S3 Endpoint** | `network` | 730 hs | $0.00 | $0.00 | Tipo **Gateway** para comunicación interna sin costo. |
| **Data Transfer Out** | `network` | 1 GB | $0.00 | $0.00 | Egress de descarga. Cubierto por Free Tier (hasta 100GB). |

*   **Costo Mensual Dev Total:** **USD 12.84**
*   **Cumplimiento del Budget:** Sí, entra con un **14.4% de margen libre** (USD 2.16 restante para red de seguridad).

---

## 3. Entorno de Producción (SaaS de Alquileres Escalado)

Para producción, la aplicación opera bajo un modelo multi-inquilino de escala moderada: **1,000 contratos procesados al mes** (SaaS en crecimiento para administradores de consorcios). Se asegura alta disponibilidad con redundancia Multi-AZ en base de datos y balanceador de carga.

### Estructura de Costos Proyectada (Prod)
| Servicio AWS | Tipo | Uso Mensual | Precio Unitario | Costo Mensual (USD) | Notas / Justificación |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Amazon RDS PostgreSQL** | `db` | 730 hs | $0.034 / hs | $24.82 | db.t3.micro (**Multi-AZ** para replicación automática de base de datos). |
| **Application Load Balancer** | `network` | 730 hs | $0.0305 / hs | $22.27 | ALB para balanceo de peticiones y alta disponibilidad ($0.0225/hs + 1 LCU). |
| **AWS Secrets Manager** | `security` | 1 secreto | $0.40 / secret | $0.40 | Almacenamiento seguro de llaves de producción. |
| **Amazon S3 (Standard)** | `storage` | 2 GB | $0.023 / GB | $0.05 | Almacenamiento activo (2 GB nuevos por mes). |
| **Amazon S3 Glacier** | `storage` | 100 GB | $0.0036 / GB | $0.36 | Archivo histórico acumulado de alquileres finalizados. |
| **AWS Lambda (ARM64)** | `compute` | 1,000 ejec. | $0.00 | $0.00 | Procesador OCR (128MB, 2s/run). Cubierto por Free Tier. |
| **Amazon SQS** | `network` | 1,000 msgs. | $0.00 | $0.00 | Buffer de amortiguación de eventos de subida. Cubierto por Free Tier. |
| **VPC S3 Endpoint** | `network` | 730 hs | $0.00 | $0.00 | Tipo Gateway gratuito para acceso privado interno a S3. |
| **Data Transfer Out** | `network` | 10 GB | $0.00 | $0.00 | Egress de usuarios interactuando con la web. Cubierto por Free Tier. |

*   **Costo Mensual Prod Total:** **USD 47.90**
*   **Cumplimiento del Budget:** Sí, entra con holgura en el presupuesto de USD 55.00 con un **12.9% de margen libre** (USD 7.10 restante).

---

## 4. Decisiones Clave de Diseño y Tradeoffs

1.  **VPC S3 Endpoint en lugar de NAT Gateway (Ahorro de ~USD 32.85/mes):**
    Una VPC privada requiere NAT Gateways para acceder a internet, pero esto añadiría un costo fijo inaceptable para una plataforma de alquileres en crecimiento. Al configurar un **VPC Endpoint S3 tipo Gateway** (gratuito) y conectores internos, la Lambda puede interactuar con S3, SQS y Secrets Manager sin gastar un solo centavo de red.
    *   *Tradeoff:* Si la aplicación SaaS decidiera integrarse en el futuro con un motor OCR externo no administrado en AWS (como una API de procesamiento de contratos externa), obligaría a contratar un NAT Gateway o una VPC Endpoint tipo Interface de costo fijo.
2.  **Transición de Almacenamiento a Glacier (Ahorro de 84% en resguardo histórico):**
    Una vez procesado el contrato y extraídos los metadatos a PostgreSQL, el documento en imagen no se vuelve a consultar a menos que ocurra una auditoría. Mantener los contratos en S3 Standard a largo plazo encarecería la factura inútilmente. Transicionar las imágenes a **Glacier Flexible Retrieval** a los 7 días reduce el costo de almacenamiento de $0.023 a $0.0036 por GB.
    *   *Tradeoff:* Si el usuario del SaaS solicita ver el contrato digitalizado original en su panel web, el sistema tardará entre 3 y 5 horas en recuperarlo de Glacier. Si el negocio requiere descarga instantánea, se debe migrar la regla hacia S3 Glacier Instant Retrieval ($0.004/GB).
3.  **Apagado Programado de base de datos en Desarrollo:**
    RDS dev representa el mayor gasto en no producción ($12.41). Si limitamos su encendido a solo horas hábiles mediante automatizaciones (ej. apagado automático los fines de semana y noches), reducimos el uso mensual a 220 hs, reduciendo el costo de RDS dev a **USD 3.74/mes** y permitiendo un FinOps óptimo.
