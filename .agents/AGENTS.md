# Reglas del Proyecto - Proyecto Final Cloud Computing

Este archivo contiene las directrices, estándares y restricciones de arquitectura para el desarrollo y aprovisionamiento de la infraestructura del proyecto final. Todos los agentes autónomos que colaboren en este repositorio deben seguir estrictamente estas reglas de desarrollo.

---

## 1. Estándares de Infraestructura (IaC & Contenedores)

- **Declarativo sobre Imperativo:** Toda la infraestructura debe definirse utilizando HCL de **OpenTofu / Terraform**. Queda prohibido el uso de scripts de AWS CLI o Boto3 para aprovisionar recursos principales, a menos que sean tareas auxiliares de limpieza o pruebas.
- **Idempotencia:** El despliegue de infraestructura debe ser reproducible y poder ejecutarse repetidas veces sin fallas.
- **LocalStack Community:** Las pruebas locales se realizan sobre el puerto `http://localhost:4566` en LocalStack. Para servicios de AWS con características Pro no soportadas en la versión Community (como RDS), emular la base de datos o servicio localmente mediante contenedores de Docker en Docker Compose.

---

## 2. Reglas de Seguridad e Identidad (IAM)

- **Principio de Menor Privilegio:** Ninguna política de IAM (`aws_iam_policy`) o rol de ejecución debe poseer permisos comodín `*` en la sección `Resource` si se puede restringir a recursos o ARNs específicos.
- **Inyección de Secretos:** Está prohibido hardcodear contraseñas, tokens o llaves de API en el código de Terraform, Dockerfiles o código de la aplicación. Utilizar variables de entorno inyectadas o integraciones de AWS Secrets Manager / Parameter Store.

---

## 3. Calidad de Código y Estilo

- **HCL Formatting:** Todo archivo de Terraform/OpenTofu debe estar formateado con `tofu fmt` o `terraform fmt` antes de ser confirmado.
- **Evitar Spanglish:** En la documentación y comentarios de código, utilizar términos técnicos correctos (ej: *VPC* en lugar de *red virtual*, *Instancia EC2* en lugar de *easy-choo*, *PostgreSQL* en lugar de *pobres*).
- **Exclusión de Estados:** El archivo de estado `terraform.tfstate` y sus copias de seguridad son confidenciales y no deben subirse jamás al control de versiones.
