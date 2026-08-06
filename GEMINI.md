# Guía de Desarrollo para Gemini (GEMINI.md)

Este archivo provee contexto general y directrices de desarrollo para los asistentes de IA (como Gemini) que colaboren en este repositorio del **Proyecto Final de Cloud Computing**.

---

## 1. Contexto del Repositorio y Entorno
El repositorio contiene la infraestructura y código de la aplicación para el entregable del proyecto integrador:
- **Automatización:** Se utiliza **OpenTofu / Terraform** para declarar los recursos de nube en la carpeta `iac/`.
- **Contenedores:** Las aplicaciones se empaquetan en imágenes de Docker y se administran localmente con Docker Compose (`compose.yaml`).
- **Pruebas Locales:** La emulación local de servicios de AWS se realiza sobre **LocalStack Community** (`http://localhost:4566`).

---

## 2. Instrucciones para la Generación de Código y Commits
Cuando propongas cambios de infraestructura o código de aplicación, asegúrate de:
- **Declarar en HCL (OpenTofu):** Todo recurso debe aprovisionarse mediante código de OpenTofu. No usar scripts de CLI imperativos para la creación.
- **Idempotencia:** La infraestructura debe poder desplegarse y destruirse limpiamente con un solo comando.
- **Seguridad:** No expongas contraseñas, tokens de API o secretos en el código. Usa variables de entorno o gestores de secretos.
- **Formateo:** Formatea los archivos `.tf` con `tofu fmt` o `terraform fmt`.
- **Evitar Spanglish:** No utilices palabras traducidas fonéticamente en documentación o logs (ej: usar *VPC* en lugar de *red virtual*, *Instancia EC2* en lugar de *easy-choo*).
- **Control de Estado:** No agregues archivos de estado `terraform.tfstate` al control de versiones.
