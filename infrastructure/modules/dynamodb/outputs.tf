output "table_name" {
  description = "Name of the DynamoDB sessions table"
  value       = aws_dynamodb_table.sessions.name
}

output "table_arn" {
  description = "ARN of the DynamoDB sessions table"
  value       = aws_dynamodb_table.sessions.arn
}

output "tasks_table_name" {
  description = "Name of the DynamoDB tasks table"
  value       = var.create_tasks_table ? aws_dynamodb_table.tasks[0].name : null
}

output "tasks_table_arn" {
  description = "ARN of the DynamoDB tasks table"
  value       = var.create_tasks_table ? aws_dynamodb_table.tasks[0].arn : null
}

# Checkpoints table outputs
output "checkpoints_table_name" {
  description = "Name of the checkpoints table"
  value       = aws_dynamodb_table.checkpoints.name
}

output "checkpoints_table_arn" {
  description = "ARN of the checkpoints table"
  value       = aws_dynamodb_table.checkpoints.arn
}
