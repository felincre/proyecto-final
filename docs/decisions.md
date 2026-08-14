# Registro de Decisiones de Arquitectura (ADR)

Este registro documenta las decisiones clave de arquitectura tomadas durante el diseño de la infraestructura para el Proyecto Final.

---

## Decisiones

### 001 — Redundancia en base de datos (RDS) y ciclo de vida en S3 (Glacier)

- **Decision:** Concentrar la redundancia y alta disponibilidad activa (Multi-AZ) en la base de datos (RDS PostgreSQL), archivar las imágenes crudas de S3 a Glacier mediante políticas de ciclo de vida (S3 Lifecycle), y omitir la replicación activa multi-región para ambos servicios.
- **Contexto:** En la nube, la alta disponibilidad tiene costo. S3 Standard ofrece por defecto replicación automática en al menos 3 Zonas de Disponibilidad (AZ) con 99.999999999% de durabilidad. No obstante, para la base de datos RDS, una instancia Single-AZ es un punto único de falla (SPOF) físico. Una vez procesado el contrato, las imágenes crudas son datos fríos e históricos, mientras que los metadatos y relaciones del negocio en la base de datos constituyen el motor activo de consulta diaria.
- **Alternativas:** 
  1. Configurar replicación de base de datos multi-región activa-activa y replicación de S3 entre regiones (S3 Cross-Region Replication - CRR).
  2. Mantener RDS en Single-AZ y S3 sin ciclo de vida (almacenamiento Standard indefinido).
- **Tradeoff:** Se decidió no implementar redundancia multi-región para optimizar costos de transferencia de salida (egress) y storage, ya que el procesamiento de contratos es asíncrono y tolera una eventual caída regional (RTO y RPO flexibles de horas). Sin embargo, se invierte en alta disponibilidad local configurando **RDS Multi-AZ** (réplica en standby síncrona en otra AZ con failover automático de <60s) para proteger la consistencia operativa, y se ahorra costo de storage archivando imágenes frías a Glacier a los 7 días.
- **Resultado:** Configurado el ciclo de vida en S3 para archivar objetos a los 7 días a Glacier. La base de datos RDS PostgreSQL se planifica con Multi-AZ habilitado (`multi_az = true`) para producción, garantizando resiliencia ante caídas de un centro de datos entero (AZ) sin intervención manual.

---


### 002 — Cómputo serverless con AWS Lambda en lugar de instancias EC2

- **Decision:** Utilizar AWS Lambda disparado por eventos de S3 en lugar de mantener una instancia EC2 encendida de forma permanente.
- **Contexto:** La ingesta y procesamiento de contratos es un patrón de carga esporádico e irregular (ocurre solo cuando un usuario o escáner sube un archivo nuevo). Mantener un servidor 24/7 consumiendo CPU y memoria en reposo es financieramente ineficiente.
- **Alternativas:** Mantener una instancia EC2 corriendo un script de escucha, o una tarea de ECS Fargate permanente.
- **Tradeoff:** Reducción drástica del costo de cómputo (escala a cero y cobra solo por los milisegundos de ejecución del procesamiento). Como contraparte, se asume una latencia de arranque en frío (cold start) en la fase de **Init** de la microVM (descarga del código y arranque del runtime), lo cual es aceptable ya que el procesamiento es asíncrono y no interactivo.
- **Optimizaciones de Rendimiento (Clase 14):**
  1. *Reutilización de conexiones en caliente (Warm Starts):* El código de la Lambda declara la lógica de inicialización del cliente de Secrets Manager y de la base de datos **fuera del handler de ejecución (en el ámbito global)**. Esto permite ejecutar la conexión pesada una única vez durante el cold start (Init phase) y mantenerla viva para reutilizarla en milisegundos durante las ejecuciones en caliente posteriores (Invoke phase).
  2. *Asignación de Memoria/CPU:* Se planifica la asignación de 512 MB de RAM. Dado que en AWS Lambda la potencia de CPU escala linealmente con la memoria asignada, esta cantidad proporciona un balance óptimo entre CPU y costos, reduciendo el tiempo de ejecución facturado (GB-segundo) y mitigando el impacto de latencias en el procesamiento.
- **Resultado:** Configurado trigger de S3 (`ObjectCreated`) directo hacia la función Lambda.


---

### 003 — Base de datos Relacional (RDS PostgreSQL) en lugar de No Relacional (DynamoDB)

- **Decision:** Almacenar los metadatos extraídos de los contratos en una base de datos relacional (RDS PostgreSQL) en lugar de una base documental o clave-valor como DynamoDB.
- **Contexto:** Los contratos comerciales tienen esquemas rígidos (IDs, montos, fechas, firmantes) y relaciones estrictas con otras entidades del negocio (clientes, proveedores, productos). Además, el negocio requiere reportes analíticos cruzados y auditorías que exigen consistencia transaccional (ACID).
- **Alternativas:** Almacenar los metadatos en DynamoDB o Amazon DocumentDB.
- **Tradeoff:** RDS PostgreSQL garantiza integridad referencial, facilita consultas complejas mediante SQL (joins) y asegura consistencia total. A cambio, RDS tiene un costo mínimo de base permanente en reposo mayor que el de DynamoDB, y requiere administrar subredes y security groups en la VPC.
- **Resultado:** Base de datos relacional planificada dentro de la subred privada de la VPC.

---

### 004 — VPC Gateway Endpoint para acceso privado a S3

- **Decision:** Utilizar un VPC Gateway Endpoint para S3 para encaminar el tráfico privado entre la Lambda y el bucket de S3 sin utilizar un NAT Gateway.
- **Contexto:** La función Lambda corre dentro de la subred privada de la VPC por motivos de seguridad (acceso a la base de datos). Para leer los contratos de S3, requiere conectividad de red con el servicio. Un NAT Gateway resolvería esto pero tiene un costo de ~$32/mes. Como S3 admite Gateway Endpoints (sin costo de procesamiento ni cargos fijos por hora), podemos rutear este tráfico internamente en AWS.
- **Alternativas:** Utilizar NAT Gateway para salida general a Internet, o VPC Interface Endpoint (que tiene costo fijo por hora).
- **Tradeoff:** Costo fijo cero ($0/mes) y latencia ultra baja al permanecer el tráfico en la red interna de AWS. El tradeoff es que los Gateway Endpoints solo sirven para S3 y DynamoDB; cualquier acceso posterior de la Lambda a internet pública requerirá un NAT Gateway.
- **Resultado:** Configurado `aws_vpc_endpoint` de tipo Gateway para el servicio S3 en la tabla de ruteo de la VPC.

---

### 005 — Emulación de base de datos RDS con contenedor PostgreSQL en Docker Compose

- **Decision:** Emular el servicio de base de datos Amazon RDS PostgreSQL localmente mediante un contenedor oficial de PostgreSQL (`postgres:16`) en Docker Compose, en lugar de intentar desplegar RDS en LocalStack.
- **Contexto:** En LocalStack Community (gratuito), las APIs de base de datos relacional (como RDS) son características exclusivas de la versión Pro. Para habilitar pruebas end-to-end locales robustas sin costo, se levanta la base de datos relacional mediante contenedores Docker estándar.
- **Alternativas:** Comprar una licencia de LocalStack Pro, o prescindir del testing con base de datos real.
- **Tradeoff:** Permite validar la interacción real del código de la Lambda con un motor SQL PostgreSQL de forma gratuita. El tradeoff es que los recursos específicos de IaC para aprovisionar `aws_db_instance` de Terraform no se ejecutan contra LocalStack, debiéndose dejar documentados u omitidos en la ejecución local mediante variables o condicionales.
- **Resultado:** Aprovisionado un servicio `db` PostgreSQL en `compose.yaml` integrado a la red Docker del proyecto.

---

### 006 — Gestión de credenciales de base de datos con AWS Secrets Manager

- **Decision:** Almacenar y recuperar dinámicamente las credenciales de conexión de la base de datos a través de AWS Secrets Manager, en lugar de definirlas en texto plano en las variables de entorno de la función Lambda o hardcodearlas en el código.
- **Contexto:** Almacenar contraseñas y nombres de usuario de base de datos en variables de entorno estándar de AWS Lambda las expone en texto plano en la consola de AWS y mediante llamadas a la API `GetFunctionConfiguration` para cualquier usuario con lectura básica. Al tratarse de un sistema con información transaccional sensible, es un riesgo de seguridad crítico e inaceptable.
- **Alternativas:**
  1. Utilizar variables de entorno de la Lambda con encriptación personalizada usando llaves AWS KMS administradas por el cliente.
  2. Almacenar credenciales en el almacén de parámetros de AWS Systems Manager (Parameter Store).
- **Tradeoff:** El uso de Secrets Manager añade el costo de almacenar el secreto (~$0.40/mes) y un costo marginal por cada 10,000 llamadas a la API. Adicionalmente, el código de la Lambda debe integrar el SDK `boto3` para realizar la llamada de red al inicio de la ejecución. Sin embargo, esto se compensa al proveer un almacenamiento fuertemente cifrado por KMS, permitir auditorías automáticas de acceso a contraseñas vía CloudTrail y posibilitar la rotación automática de claves en el motor de base de datos en producción.
- **Resultado:** Declarados los recursos `aws_secretsmanager_secret` y `aws_secretsmanager_secret_version` en OpenTofu y mapeado el permiso `secretsmanager:GetSecretValue` en la política IAM de ejecución de la Lambda.

---

### 007 — Desacoplamiento del trigger: Uso de colas SQS intermedias y Dead Letter Queue (DLQ)

- **Decision:** Interponer una cola de mensajería **AWS SQS** y una **Dead Letter Queue (DLQ)** para canalizar los eventos de carga de S3 y disparar la ejecución de la Lambda mediante un Event Source Mapping, en lugar de realizar notificaciones directas S3-to-Lambda.
- **Contexto:** En la arquitectura serverless orientada a eventos, cuando un archivo se sube a S3, el trigger directo puede causar picos inmanejables de concurrencia que saturen el pool de conexiones de la base de datos (PostgreSQL/RDS). Desacoplar la ingesta permite amortiguar ráfagas, controlar la tasa de ejecución (rate limiting) y aislar mensajes corruptos.
- **Alternativas:**
  1. Utilizar una notificación directa de eventos S3-to-Lambda (`aws_s3_bucket_notification` directa a la ARN de la Lambda).
  2. Implementar un bus de eventos más complejo con Amazon EventBridge o tópicos Amazon SNS.
- **Tradeoff:** Añade la complejidad de aprovisionar y configurar la cola, su política de acceso y el mapeo de origen de eventos (`aws_lambda_event_source_mapping`) en OpenTofu, y requiere que la Lambda parsee eventos wrapped por SQS en el JSON de entrada. Sin embargo, esto proporciona tolerancia a fallos completa (si la base de datos se cae, los mensajes esperan hasta 4 días en la cola) y desvía automáticamente "poison messages" a la DLQ tras 3 reintentos fallidos, protegiendo al sistema.
- **Resultado:** Aprovisionadas las colas `aws_sqs_queue.contracts_queue` y `aws_sqs_queue.contracts_dlq`, la política de SQS, el bucket notification hacia SQS y el event source mapping hacia la Lambda en OpenTofu, y adaptado el código de la Lambda para procesar los payloads encolados.

---

### 008 — Elección de tecnología de mensajería: Cola (SQS) en lugar de Bus (EventBridge) o Streaming Log (Kinesis/Kafka)

- **Decision:** Utilizar una cola de mensajes simple (**Amazon SQS**) con reintentos y Dead Letter Queue (DLQ) para encolar las tareas de procesamiento, en lugar de un bus de eventos (**Amazon EventBridge**) o un log distribuido de streaming (**Amazon Kinesis Data Streams / Apache Kafka**).
- **Contexto:** En arquitecturas orientadas a eventos (Clase 15), es crucial diferenciar entre:
  1. *Cola (SQS):* Procesamiento punto a punto de tareas. El mensaje se elimina al ser procesado exitosamente. No hay replay.
  2. *Bus de Eventos (EventBridge):* Enrutamiento inteligente a múltiples targets según patrones declarativos JSON. Sin control de tasa de consumo.
  3. *Streaming Log (Kinesis/Kafka):* Persistencia de flujos de eventos a escala masiva por tiempo configurable. Permite consumo concurrente por distintos grupos y replay (retroceder offsets).
  La aplicación procesa imágenes de contratos de alquiler que se suben de forma esporádica. No requerimos análisis de telemetría a escala de gigabytes por segundo, sino procesar de forma secuencial y ordenada cada contrato cargado asegurando tolerancia a fallos.
- **Alternativas:**
  1. *Amazon EventBridge:* Adecuado para notificar a múltiples servicios independientes sobre la subida del contrato (ej. auditoría, finanzas, notificaciones). Sin embargo, para la tarea de procesamiento unitaria e individual (extracción de metadatos), carece de soporte nativo de cola de trabajo estructurada y control de concurrencia a nivel de BD.
  2. *Amazon Kinesis / Apache Kafka (Redpanda):* Hubiese permitido conservar el historial de contratos subidos en el propio log para realizar futuros reprocesamientos o "replays" desde el principio del historial (TRIM_HORIZON). Sin embargo, añade un costo fijo alto (mínimo de ~$11/mes por shard en Kinesis, u hospedaje de brokers) y una complejidad de desarrollo no justificada para el volumen de la aplicación.
- **Tradeoff:**
  - *Ventajas de SQS:* Costo cero en reposo (escala a cero absoluto), manejo nativo de reintentos con descarte automático a DLQ tras 3 fallos (protección contra poison messages), y mecanismo de visibilidad temporal que previene el procesamiento duplicado del mismo contrato.
  - *Desventajas:* El mensaje se elimina permanentemente una vez procesado (no hay replay desde la cola; un reprocesamiento histórico requeriría leer directamente del bucket S3). Si en el futuro otro sistema del negocio requiere enterarse de la subida, se deberá modificar la arquitectura para implementar un patrón Fan-out (ej. S3 ➔ SNS/EventBridge ➔ SQS).
- **Resultado:** Se seleccionó SQS debido a que se trata de una cola de procesamiento de trabajos clásica que prioriza los reintentos y el descarte automatizado a DLQ a un costo óptimo de desarrollo y presupuesto.

---

### 009 — Estrategia de procesamiento de documentos: Simulación (Mock) local y proyección con Amazon Textract (OCR) + Amazon Bedrock (LLM Scraping) en producción

- **Decision:** Utilizar una arquitectura simulada (Mock) durante el desarrollo local, y definir como arquitectura productiva el uso combinado de **Amazon Textract** (para la extracción de texto/OCR de la imagen) junto con **Amazon Bedrock (LLM)** para el raspado semántico (*scraping*) y estructuración de metadatos en formato JSON.
- **Contexto:** Actualmente, la Lambda de desarrollo simula la base de datos e inserta valores ficticios para evitar emular servicios complejos de IA de forma local y mantener portabilidad. Sin embargo, para la solución real en producción, procesar contratos de alquiler escritos con lenguaje natural variable requiere dos fases:
  1. *OCR:* Traducir pixeles de la imagen a caracteres de texto.
  2. *Scraping / Extracción Semántica:* Entender el contexto para extraer variables específicas (fecha de vigencia, nombres de inquilino/propietario, depósitos y montos de alquiler).
- **Alternativas:**
  1. *Parser por Expresiones Regulares (Regex):* Buscar palabras clave (ej: "monto", "inquilino") mediante patrones de texto rígidos sobre el OCR. Es muy frágil ante variaciones de redacción o formatos de contratos.
  2. *Procesamiento OCR local (Tesseract) en Lambda:* Empaquetar binarios de Tesseract en la Lambda. Aumenta drásticamente el tamaño del zip (Cold Starts severos) y consume demasiada CPU/RAM en la Lambda (aumento de costo).
  3. *Amazon Textract + Amazon Bedrock:* Textract realiza el OCR altamente optimizado como servicio administrado. Posteriormente, el texto extraído se envía como prompt a un LLM en Bedrock (ej: Claude 3.5 Sonnet / Llama 3) con un esquema JSON estructurado para extraer los datos mediante razonamiento semántico.
- **Tradeoff:**
  - *Ventajas del enfoque Textract + Bedrock:*
    - Flexibilidad absoluta ante cualquier formato o redacción de contrato de alquiler.
    - El LLM puede inferir información que no está explícitamente etiquetada mediante razonamiento semántico (ej: identificar la moneda o deducir penalidades).
    - Costo bajo al operar bajo demanda por token/petición, sin servidores ni mantenimiento de binarios OCR complejos en la Lambda.
  - *Desventajas:* Añade latencia de red al consultar dos APIs externas (Textract y Bedrock) dentro de la Lambda, y requiere implementar técnicas de control de costos y prompts robustos frente a posibles alucinaciones del modelo.
- **Resultado:** Se aprueba la simulación (mock) en desarrollo local para viabilidad académica, y se establece como diseño productivo oficial el flujo `Imagen ➔ S3 ➔ Lambda ➔ Amazon Textract (OCR) ➔ Amazon Bedrock (LLM / Scraping Semántico) ➔ PostgreSQL`.

---

### 010 — Estructura analítica del almacenamiento: Data Lake por Zonas (S3) y formato Parquet para escalabilidad de reportería

- **Decision:** Definir que el almacenamiento analítico a largo plazo de contratos y sus metadatos estructurados se organice como un **Data Lake en Amazon S3 distribuido por zonas de madurez** (Landing, Raw, Curated, Consumer) utilizando formatos columnares de alto rendimiento (**Apache Parquet**) y catálogos de datos administrados (**AWS Glue Data Catalog + Amazon Athena**), en lugar de realizar consultas analíticas cruzadas e históricas directamente sobre la base de datos relacional de producción (PostgreSQL/RDS).
- **Contexto:** En arquitecturas de datos modernas (Clase 16), el motor transaccional (OLTP) de base de datos no debe ser estresado con consultas analíticas pesadas (OLAP) ni reportes de agregación histórica. Adicionalmente, el almacenamiento de metadatos en texto plano (como JSON) o archivos crudos (como imágenes `.jpg`) es ineficiente de consultar directamente. Para escalar la reportería de la plataforma de alquileres, se asumen las siguientes definiciones por zona de datos:
  1. *Landing (S3):* Contratos crudos (`.jpg`) tal como llegan desde el escáner del usuario con metadatos de ingesta. Actúa como backup inmutable.
  2. *Raw (S3):* Conversión automática de imágenes a texto plano Parquet particionado por `fecha_registro` (sin limpieza de calidad, conservando PII) para optimizar búsquedas.
  3. *Curated (S3):* Datos limpios, tipados, deduplicados y con PII enmascarada (ej. encriptar o censurar nombres de inquilinos y números de documentos) para cumplimiento regulatorio.
  4. *Consumer (S3):* Tablas agregadas listas para BI (ej. valor de alquiler promedio mensual, tasa de morosidad, etc.).
- **Alternativas:**
  1. *Ejecutar reportes sobre RDS PostgreSQL:* Aumenta el costo de RDS (requiere CPU/RAM adicionales) y expone datos transaccionales sensibles.
  2. *Mantener todo el Data Lake en archivos JSON crudos:* Athena cobraría altos montos ya que JSON no permite *partition pruning* eficiente ni lectura columnar (Athena factura $5.00 por TB escaneado). Parquet comprime hasta un 90% el tamaño físico y permite leer solo las columnas necesarias.
- **Tradeoff:**
  - *Ventajas:*
    - Desacoplamiento total del procesamiento transaccional respecto de la analítica de negocio.
    - Costos de consulta virtualmente nulos al combinar Parquet (columnar) con particionado por fecha en S3.
    - Cumplimiento estricto de seguridad de datos aislando la zona *Curated* (con PII protegida) de la zona *Consumer* (apta para analistas de negocio).
  - *Desventajas:* Requiere aprovisionar y orquestar pipelines ETL adicionales (ej. AWS Glue o AWS Lambda) para transformar datos de una zona a otra, y administrar catálogos de metadatos mediante AWS Glue Data Catalog (Trino/Presto).
- **Resultado:** Aprobado el diseño de Data Lake por zonas sobre S3 para la fase analítica en producción, indexado mediante AWS Glue y consultado vía Amazon Athena.

---

### 011 — Modularización de IaC y Estructuración Multi-ambiente para el Aislamiento de Entornos

- **Decisión:** Mantener una estructura de directorios de infraestructura unificada (`iac/`) parametrizada mediante variables en lugar de implementar una modularización completa con directorios físicos separados para `dev` y `prod` (Clase 17), justificando esta decisión para optimizar la portabilidad académica y la emulación local simplificada del proyecto.
- **Contexto:** En despliegues empresariales reales (Clase 17), la buena práctica exige estructurar el código de IaC utilizando **Módulos de Terraform/OpenTofu** (código reutilizable y parametrizado) y separar físicamente los archivos de estado (`.tfstate`) en directorios distintos para desarrollo y producción (`envs/dev` y `envs/prod`). Esto aísla los entornos y evita que un error de configuración en desarrollo destruya recursos de producción por accidente. Sin embargo, en el contexto de este proyecto final y su demo local:
  1. La infraestructura se emula localmente sobre un único contenedor de LocalStack.
  2. El entorno se despliega de forma automática en GitHub Codespaces mediante scripts bash automatizados de un solo clic.
- **Alternativas:**
  1. *Modularizar el código de S3, Lambda y RDS en la estructura dev/prod de la Clase 17:* Requiere crear directorios duplicados, inicializar OpenTofu de forma independiente en cada carpeta y reescribir los scripts de deploy locales para apuntar a múltiples rutas de estado.
  2. *Mantener la estructura unificada parametrizada (Elegida):* Utilizar un único directorio `iac/` y controlar la creación de recursos de producción (como el RDS Multi-AZ o el Security Group dedicado de RDS) de forma dinámica usando condicionales (`count = var.environment == "prod" ? 1 : 0`).
- **Tradeoff:**
  - *Ventajas:*
    - **Portabilidad extrema:** Permite levantar el Codespace e iniciar la demostración E2E con un único comando `./scripts/01-deploy-infra.sh` sin requerir inicializaciones secuenciales y complejas de Terraform en múltiples carpetas.
    - **Simplicidad operativa:** Menor cantidad de archivos para revisión y mayor velocidad de ejecución en la máquina local/Codespaces del evaluador.
    - **Control dinámico:** Uso eficiente de lógica condicional en HCL sin duplicar archivos.
  - *Desventajas:* Si el proyecto escala a un despliegue en la nube real con múltiples cuentas de AWS, la falta de separación física de directorios por entorno incrementa el riesgo de errores operativos (por ejemplo, aplicar cambios de pruebas sobre la cuenta productiva).
- **Resultado:** Se mantiene la estructura unificada parametrizada en la carpeta `iac/` por motivos de simplicidad y portabilidad en el desarrollo/evaluación local, asumiendo la reestructuración a carpetas multi-ambiente (`envs/dev` y `envs/prod`) con módulos reutilizables como la primera tarea del roadmap de pase a producción.








