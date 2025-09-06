# Terraform configuration for Lambda Layer deployment
# This file can be used independently or integrated with the main infrastructure

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# Variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-ppt-assistant"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "layer_name" {
  description = "Name of the Lambda layer"
  type        = string
  default     = "ai-ppt-assistant-dependencies"
}

variable "python_version" {
  description = "Python runtime version"
  type        = string
  default     = "python3.13"
}

variable "architectures" {
  description = "Compatible architectures"
  type        = list(string)
  default     = ["arm64"]
}

variable "build_method" {
  description = "Build method (docker or local)"
  type        = string
  default     = "docker"
}

# Local variables
locals {
  layer_zip_path = "${path.module}/dist/${var.layer_name}.zip"
  build_script   = "${path.module}/build.sh"
}

# Null resource to build the layer
resource "null_resource" "build_layer" {
  # Rebuild when requirements change
  triggers = {
    requirements = filemd5("${path.module}/requirements.txt")
    build_script = filemd5(local.build_script)
  }

  provisioner "local-exec" {
    command = var.build_method == "docker" ? "${local.build_script}" : "${local.build_script} --local"
    working_dir = path.module
  }
}

# Data source to wait for the build
data "local_file" "layer_zip" {
  depends_on = [null_resource.build_layer]
  filename   = local.layer_zip_path
}

# Lambda Layer Version
resource "aws_lambda_layer_version" "main" {
  filename                 = data.local_file.layer_zip.filename
  layer_name              = "${var.project_name}-${var.environment}-dependencies"
  description             = "Shared dependencies for ${var.project_name} Lambda functions"
  compatible_runtimes     = [var.python_version]
  compatible_architectures = var.architectures
  
  # Use source code hash for versioning
  source_code_hash = filebase64sha256(data.local_file.layer_zip.filename)

  # License
  license_info = "MIT"
}

# SSM Parameter to store layer ARN (for easy reference)
resource "aws_ssm_parameter" "layer_arn" {
  name  = "/${var.project_name}/${var.environment}/lambda/layer-arn"
  type  = "String"
  value = aws_lambda_layer_version.main.arn
  
  description = "ARN of the Lambda layer for ${var.project_name}"
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Lambda Layer ARN"
  }
}

# Outputs
output "layer_arn" {
  description = "ARN of the Lambda layer"
  value       = aws_lambda_layer_version.main.arn
}

output "layer_version" {
  description = "Version of the Lambda layer"
  value       = aws_lambda_layer_version.main.version
}

output "layer_source_code_hash" {
  description = "Source code hash of the layer"
  value       = aws_lambda_layer_version.main.source_code_hash
}

output "layer_source_code_size" {
  description = "Size of the layer in bytes"
  value       = aws_lambda_layer_version.main.source_code_size
}

output "ssm_parameter_name" {
  description = "Name of the SSM parameter storing the layer ARN"
  value       = aws_ssm_parameter.layer_arn.name
}