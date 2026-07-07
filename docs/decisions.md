# Registro de Decisiones de Arquitectura (ADR)

Este registro documenta las decisiones clave de arquitectura tomadas durante el diseño de la infraestructura para el Proyecto Final.

---

## Decisiones

### 001 — Redundancia en base de datos (RDS) y ciclo de vida en S3 (Glacier)

- **Decision:** Centrar la redundancia activa en la base de datos (RDS PostgreSQL) y archivar los archivos crudos de S3 a Glacier mediante políticas de ciclo de vida (S3 Lifecycle), sin implementar replicación activa multi-región de S3.
- **Contexto:** Una vez que la Lambda procesa el contrato y extrae la información relevante, la imagen cruda (.jpg) en S3 se convierte en datos "fríos" e históricos. Toda la información "caliente" de consulta diaria reside en la base de datos.
- **Alternativas:** Replicar activamente el bucket de S3 entre regiones (S3 CRR) o mantener los archivos de imagen en almacenamiento caliente standard de por vida.
- **Tradeoff:** Se ahorra costo de transferencia y almacenamiento de red al no duplicar las imágenes por múltiples regiones y al moverlas a Glacier. A cambio, concentramos la inversión de tolerancia a fallos en la base de datos mediante réplicas de lectura o Multi-AZ, que es el verdadero núcleo de consulta del negocio.
- **Resultado:** Configurado el ciclo de vida en S3 para archivar objetos a los 7 días a Glacier. La base de datos RDS PostgreSQL se planifica con Multi-AZ en producción.

---

### 002 — Cómputo serverless con AWS Lambda en lugar de instancias EC2

- **Decision:** Utilizar AWS Lambda disparado por eventos de S3 en lugar de mantener una instancia EC2 encendida de forma permanente.
- **Contexto:** La ingesta y procesamiento de contratos es un patrón de carga esporádico e irregular (ocurre solo cuando un usuario o escáner sube un archivo nuevo). Mantener un servidor 24/7 consumiendo CPU y memoria en reposo es financieramente ineficiente.
- **Alternativas:** Mantener una instancia EC2 corriendo un script de escucha, o una tarea de ECS Fargate permanente.
- **Tradeoff:** Reducción drástica del costo de cómputo (escala a cero y cobra solo por los milisegundos de ejecución del procesamiento). Como contraparte, se asume una latencia de arranque en frío (cold start) en las ejecuciones que ocurran tras períodos de inactividad, lo cual es aceptable ya que el procesamiento de contratos es una tarea asíncrona no interactiva.
- **Resultado:** Configurado trigger de S3 (`ObjectCreated`) directo hacia la función Lambda.

---

### 003 — Base de datos Relacional (RDS PostgreSQL) en lugar de No Relacional (DynamoDB)

- **Decision:** Almacenar los metadatos extraídos de los contratos en una base de datos relacional (RDS PostgreSQL) en lugar de una base documental o clave-valor como DynamoDB.
- **Contexto:** Los contratos comerciales tienen esquemas rígidos (IDs, montos, fechas, firmantes) y relaciones estrictas con otras entidades del negocio (clientes, proveedores, productos). Además, el negocio requiere reportes analíticos cruzados y auditorías que exigen consistencia transaccional (ACID).
- **Alternativas:** Almacenar los metadatos en DynamoDB o Amazon DocumentDB.
- **Tradeoff:** RDS PostgreSQL garantiza integridad referencial, facilita consultas complejas mediante SQL (joins) y asegura consistencia total. A cambio, RDS tiene un costo mínimo de base permanente en reposo mayor que el de DynamoDB, y requiere administrar subredes y security groups en la VPC.
- **Resultado:** Base de datos relacional planificada dentro de la subred privada de la VPC.
