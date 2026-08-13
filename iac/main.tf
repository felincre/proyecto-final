# -------------------------------------------------------------
# 1. Red (VPC, Subnet, Route Table, Gateway Endpoint)
# -------------------------------------------------------------

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}a"

  tags = {
    Name        = "${var.project_name}-private-subnet"
    Environment = var.environment
  }
}

# Subred privada secundaria en AZ diferente para soportar RDS Multi-AZ en producción
resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}b"

  tags = {
    Name        = "${var.project_name}-private-subnet-b"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-private-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# S3 Gateway Endpoint (Tráfico privado directo sin pasar por internet/NAT Gateway)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name        = "${var.project_name}-s3-endpoint"
    Environment = var.environment
  }
}

# -------------------------------------------------------------
# 2. Almacenamiento (S3 Bucket, Versioning, Lifecycle, Policy)
# -------------------------------------------------------------

resource "aws_s3_bucket" "raw_contracts" {
  bucket        = "${var.project_name}-raw-contracts"
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-raw-contracts-bucket"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "raw_contracts" {
  bucket = aws_s3_bucket.raw_contracts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_contracts" {
  bucket = aws_s3_bucket.raw_contracts.id

  rule {
    id     = "archive-to-glacier-after-7-days"
    status = "Enabled"

    filter {}

    transition {
      days          = 7
      storage_class = "GLACIER"
    }
  }
}

# S3 Bucket Policy: restringe el acceso al bucket permitiendo solo tráfico originado desde el VPC Endpoint 
# o llamadas del usuario root (awslocal en pruebas locales).
resource "aws_s3_bucket_policy" "raw_contracts" {
  bucket = aws_s3_bucket.raw_contracts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowOnlyVPCEndpointTraffic"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.raw_contracts.arn,
          "${aws_s3_bucket.raw_contracts.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:sourceVpce" = aws_vpc_endpoint.s3.id
          }
          ArnNotEquals = {
            "aws:PrincipalArn" = "arn:aws:iam::000000000000:root"
          }
        }
      }
    ]
  })
}

# -------------------------------------------------------------
# 3. Grupos de Seguridad (Security Groups)
# -------------------------------------------------------------

resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-lambda-sg"
  description = "Security Group for Lambda Contract Processor"
  vpc_id      = aws_vpc.main.id

  # Permitir todo el tráfico saliente (egress) para conectarse a Postgres y S3
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-lambda-sg"
    Environment = var.environment
  }
}

# -------------------------------------------------------------
# 4. Seguridad e Identidades (IAM Role, Policies)
# -------------------------------------------------------------

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-lambda-exec-role"
    Environment = var.environment
  }
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-lambda-policy"
  description = "Policy for Lambda contract processor to access S3, Secrets Manager, SQS and CloudWatch Logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_contracts.arn,
          "${aws_s3_bucket.raw_contracts.arn}/*"
        ]
      },
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn
        ]
      },
      {
        Sid    = "VPCNetworkAccess"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/*"
      },
      {
        Sid    = "SQSQueueAccess"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.contracts_queue.arn
        ]
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-lambda-policy"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# -------------------------------------------------------------
# 5. Secrets Manager (Database Credentials)
# -------------------------------------------------------------

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}-db-credentials"
  description = "Connection details for PostgreSQL database"

  tags = {
    Name        = "${var.project_name}-db-credentials"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials_version" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    host     = "proyecto-postgres" # Host del contenedor en compose.yaml
    port     = 5432
    dbname   = "contracts_db"
    username = "postgres"
    password = var.db_password
  })
}

# -------------------------------------------------------------
# 6. Cómputo (AWS Lambda Function) y Mensajería (SQS, DLQ, Event Source Mapping)
# -------------------------------------------------------------

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/contract_processor.py"
  output_path = "${path.module}/../src/contract_processor.zip"
}

resource "aws_lambda_function" "contract_processor" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = "${var.project_name}-contract-processor"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "contract_processor.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30

  # Configuración VPC para ejecutar la Lambda en subred privada
  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_SECRET_NAME = aws_secretsmanager_secret.db_credentials.name
      AWS_REGION     = var.region
    }
  }

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  tags = {
    Name        = "${var.project_name}-contract-processor"
    Environment = var.environment
  }
}

# SQS Queue for buffering raw contract ingestion events
resource "aws_sqs_queue" "contracts_queue" {
  name                      = "${var.project_name}-contracts-queue"
  delay_seconds             = 0
  max_message_size          = 262144 # 256 KB
  message_retention_seconds = 345600 # 4 days
  receive_wait_time_seconds = 10     # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.contracts_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.project_name}-contracts-queue"
    Environment = var.environment
  }
}

# Dead Letter Queue (DLQ) for failed contract processing attempts
resource "aws_sqs_queue" "contracts_dlq" {
  name                      = "${var.project_name}-contracts-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name        = "${var.project_name}-contracts-dlq"
    Environment = var.environment
  }
}

# SQS Policy: Permite a S3 enviar mensajes a la cola SQS
resource "aws_sqs_queue_policy" "contracts_queue_policy" {
  queue_url = aws_sqs_queue.contracts_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowS3ToSendMessage"
        Effect    = "Allow"
        Principal = "*"
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.contracts_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_s3_bucket.raw_contracts.arn
          }
        }
      }
    ]
  })
}

# Configuración de notificación del Bucket S3 para enviar eventos a la cola SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.raw_contracts.id

  queue {
    queue_arn     = aws_sqs_queue.contracts_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_suffix = ".jpg"
  }

  depends_on = [aws_sqs_queue_policy.contracts_queue_policy]
}

# Mapeo de evento SQS a Lambda (Event Source Mapping)
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.contracts_queue.arn
  function_name    = aws_lambda_function.contract_processor.arn
  batch_size       = 1
  enabled          = true
}

# -------------------------------------------------------------
# 7. Producción RDS PostgreSQL (Simulado localmente con Docker Compose)
# -------------------------------------------------------------

resource "aws_db_subnet_group" "db_subnet_group" {
  count      = var.environment == "prod" ? 1 : 0
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = [aws_subnet.private.id, aws_subnet.private_b.id]

  tags = {
    Name        = "${var.project_name}-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_db_instance" "postgres" {
  count                  = var.environment == "prod" ? 1 : 0
  identifier             = "${var.project_name}-db"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  db_name                = "contracts_db"
  username               = "postgres"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group[0].name
  vpc_security_group_ids = [aws_security_group.lambda.id]
  skip_final_snapshot    = true
  multi_az               = true # Configuración Multi-AZ (ADR 001)

  tags = {
    Name        = "${var.project_name}-rds"
    Environment = var.environment
  }
}
