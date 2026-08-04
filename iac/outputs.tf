output "raw_contracts_bucket_name" {
  value       = aws_s3_bucket.raw_contracts.id
  description = "Nombre del bucket S3 de contratos crudos"
}

output "lambda_function_name" {
  value       = aws_lambda_function.contract_processor.function_name
  description = "Nombre de la funcion Lambda del procesador"
}

output "lambda_role_arn" {
  value       = aws_iam_role.lambda_exec.arn
  description = "ARN del rol de ejecucion de la Lambda"
}

output "db_credentials_secret_name" {
  value       = aws_secretsmanager_secret.db_credentials.name
  description = "Nombre del secreto en Secrets Manager para la base de datos"
}

output "vpc_id" {
  value       = aws_vpc.main.id
  description = "ID de la VPC principal"
}

output "private_subnet_id" {
  value       = aws_subnet.private.id
  description = "ID de la subred privada"
}
