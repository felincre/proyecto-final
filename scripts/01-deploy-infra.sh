#!/usr/bin/env bash
# Deploy local-first infrastructure using OpenTofu (Terraform).
# Idempotente: Se puede ejecutar múltiples veces sin romper nada.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== [1/2] Inicializando OpenTofu ==="
cd "$ROOT/iac"
tofu init

echo "=== [2/2] Aplicando infraestructura en LocalStack ==="
tofu apply -auto-approve

echo "=== Despliegue completado con éxito ==="
