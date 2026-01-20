# Main Terraform configuration for Email Cleanup System
# This file defines all AWS resources needed for Lambda deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================================================
# IAM ROLE FOR LAMBDA
# ============================================================================

resource "aws_iam_role" "lambda_role" {
  name = "email-cleanup-lambda-role"

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
}

# Allow Lambda to write logs to CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow Lambda to read from Secrets Manager
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "lambda-secrets-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:gmail-credentials*"
      }
    ]
  })
}

# ============================================================================
# LAMBDA FUNCTION
# ============================================================================

resource "aws_lambda_function" "email_cleanup" {
  filename         = "lambda-deployment.zip"
  function_name    = "email-cleanup-system"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256
  source_code_hash = filebase64sha256("lambda-deployment.zip")

  environment {
    variables = {
      DRY_RUN = "false"
    }
  }

  depends_on = [aws_iam_role_policy.lambda_secrets]
}

# ============================================================================
# EVENTBRIDGE RULE FOR SCHEDULING
# ============================================================================

resource "aws_cloudwatch_event_rule" "email_cleanup_schedule" {
  name                = "email-cleanup-daily"
  description         = "Daily email cleanup at 9 AM"
  schedule_expression = "cron(0 9 * * ? *)"
  state               = var.eventbridge_enabled ? "ENABLED" : "DISABLED"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.email_cleanup_schedule.name
  target_id = "EmailCleanupLambda"
  arn       = aws_lambda_function.email_cleanup.arn
}

# Allow EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_cleanup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.email_cleanup_schedule.arn
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_caller_identity" "current" {}

# ============================================================================
# OUTPUTS
# ============================================================================

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.email_cleanup.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.email_cleanup.function_name
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.email_cleanup_schedule.name
}

output "iam_role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.lambda_role.arn
}
