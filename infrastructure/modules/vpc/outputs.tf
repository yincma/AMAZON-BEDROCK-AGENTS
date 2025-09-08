# Outputs for VPC Module

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = var.enable_nat_gateway ? aws_nat_gateway.main[*].id : []
}

output "lambda_security_group_id" {
  description = "Security group ID for Lambda functions"
  value       = aws_security_group.lambda.id
}

output "vpc_endpoints_security_group_id" {
  description = "Security group ID for VPC endpoints"
  value       = aws_security_group.vpc_endpoints.id
}

output "vpc_endpoint_ids" {
  description = "VPC endpoint IDs"
  value = var.enable_vpc_endpoints ? {
    s3                    = length(aws_vpc_endpoint.s3) > 0 ? aws_vpc_endpoint.s3[0].id : null
    dynamodb              = length(aws_vpc_endpoint.dynamodb) > 0 ? aws_vpc_endpoint.dynamodb[0].id : null
    bedrock_runtime       = length(aws_vpc_endpoint.bedrock_runtime) > 0 ? aws_vpc_endpoint.bedrock_runtime[0].id : null
    bedrock_agent_runtime = length(aws_vpc_endpoint.bedrock_agent_runtime) > 0 ? aws_vpc_endpoint.bedrock_agent_runtime[0].id : null
    lambda                = length(aws_vpc_endpoint.lambda) > 0 ? aws_vpc_endpoint.lambda[0].id : null
    cloudwatch_logs       = length(aws_vpc_endpoint.cloudwatch_logs) > 0 ? aws_vpc_endpoint.cloudwatch_logs[0].id : null
    sqs                   = var.enable_sqs_endpoint && length(aws_vpc_endpoint.sqs) > 0 ? aws_vpc_endpoint.sqs[0].id : null
  } : {}
}

output "private_route_table_ids" {
  description = "IDs of the private route tables"
  value       = aws_route_table.private[*].id
}

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}