# Input variables for Terraform configuration

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "eventbridge_enabled" {
  description = "Enable EventBridge rule for scheduled execution"
  type        = bool
  default     = true
}
