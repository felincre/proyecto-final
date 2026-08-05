# Plan de Resiliencia, Alta Disponibilidad y Disaster Recovery (Clase 13)

Este documento detalla el análisis de resiliencia del **Ingestador de Contratos Serverless** bajo las directrices de la Clase 13. Evaluamos los puntos únicos de falla (SPOFs), definimos las métricas operativas de negocio (RTO/RPO) y establecemos la estrategia ante desastres (Disaster Recovery).

---

## 1. Análisis de Puntos Únicos de Falla (SPOF) y Mitigación

A continuación se identifican los componentes críticos de la arquitectura física y su respectiva mitigación para garantizar la continuidad operativa en AWS:

| Componente | Riesgo / SPOF Identificado | Estrategia de Mitigación (Cloud) | Implementación en Código IaC |
| :--- | :--- | :--- | :--- |
| **Almacenamiento (S3)** | Eliminación accidental o ataque de ransomware sobre los contratos digitales. | Activación de versionado de objetos y almacenamiento redundante de Glacier. | Recurso `aws_s3_bucket_versioning` activo y política de transición a Glacier a los 7 días. |
| **Cómputo (Lambda)** | Saturación por carga masiva concurrente de imágenes que agote la capacidad de procesamiento o colapse la BD. | Desacoplamiento temporal del trigger mediante cola de mensajería (SQS) para control de tasa (rate-limiting). | Planificado en arquitectura y registrado en el **ADR-007** (Trigger directo vs SQS). |
| **Base de Datos (RDS)** | Caída física de la zona de disponibilidad (AZ) o falla del hardware de la base de datos PostgreSQL. | Configuración de **RDS Multi-AZ** (base primaria activa + standby síncrona pasiva en otra AZ con failover automático de <60s). | Condicional `multi_az = true` para producción configurado en `main.tf` sobre el recurso `aws_db_instance`. |
| **Conectividad de Red** | Interrupción en la salida a Internet o saturación de enlaces NAT para acceder a S3. | Uso de un **VPC Gateway Endpoint** privado para rutear el tráfico de S3 de manera interna y gratuita. | Declaración de `aws_vpc_endpoint` de tipo "Gateway" asociado a las tablas de ruteo privadas en `main.tf`. |
| **Monitoreo y Costos** | Desborde financiero por ejecuciones infinitas de Lambda (FinOps) o fallos silenciosos en la ingesta. | Configuración de **AWS Budgets** mensuales y alarmas de facturación en CloudWatch mediante Amazon SNS. | Detallado en el plan de mitigación operativa del proyecto. |

---

## 2. Métricas de Negocio: RTO y RPO

El diseño de resiliencia de la plataforma está dimensionado para cumplir con las siguientes métricas de recuperación acordadas con el negocio para un sistema de procesamiento asíncrono de documentos:

### RTO (Recovery Time Objective) — Tiempo Máximo de Inactividad Tolerable
* **Objetivo de RTO:** **4 Horas**.
* **Justificación técnica:** 
  * Ante la falla de una zona de disponibilidad entera, el failover de la base de datos (RDS Multi-AZ) es automático y toma **menos de 60 segundos** sin requerir intervención del usuario o de DNS (gracias al registro CNAME persistente provisto por AWS).
  * Ante un desastre regional total de AWS (ej. caída completa de `us-east-1`), la infraestructura es 100% reproducible. Un operador puede aplicar la IaC en una región alternativa (como `us-west-2`) ejecutando `tofu apply` en **menos de 10 minutos**.

### RPO (Recovery Point Objective) — Pérdida Máxima de Datos Tolerable
* **Objetivo de RPO:** **5 Minutos**.
* **Justificación técnica:**
  * Para los contratos almacenados en S3, la durabilidad de S3 Standard (que replica objetos de manera inmediata en al menos 3 AZs independientes) garantiza que no habrá pérdida de archivos ya confirmados en la API.
  * Para los metadatos transaccionales, la replicación de RDS es **síncrona** hacia la zona de disponibilidad en standby. Esto significa que cualquier transacción SQL confirmada por la Lambda antes del fallo de la AZ principal se encuentra replicada al 100%, logrando un **RPO de 0 segundos** para datos transaccionales.
  * Solo aquellos contratos que estuviesen en tránsito de subida exacta al momento del fallo podrían requerir que el cliente los vuelva a enviar (dentro del margen de los 5 minutos de RPO).

---

## 3. Estrategia de Disaster Recovery (DR)

De acuerdo a las opciones oficiales de AWS y los costos asociados de FinOps, el proyecto adopta una estrategia híbrida:

1. **A Nivel Zonal (Zonal Failover):** **Active-Passive Multi-AZ**.
   * La aplicación de cómputo (Lambda) escala de forma transparente entre las zonas de disponibilidad de la región.
   * La base de datos opera bajo un esquema activo-pasivo donde la réplica de standby no recibe lecturas directas pero asume la identidad primaria de inmediato tras una caída física de la AZ principal.
2. **A Nivel Regional (Regional Disaster Recovery):** **Backup & Restore (Copia de Seguridad y Restauración)**.
   * Mantener una infraestructura Multi-Site Active-Active en dos regiones distintas duplicaría los costos fijos mensuales (RDS activo, replicación de S3, tráfico de red de salida egress).
   * Dado que el procesamiento de contratos no requiere respuesta interactiva instantánea en tiempo real de milisegundos, el negocio prefiere optimizar costos. En caso de fallo regional catastrófico, se levantará la infraestructura desde cero usando OpenTofu y se restaurarán los datos de la base de datos utilizando los snapshots automatizados diarios guardados de forma segura en buckets con retención.
