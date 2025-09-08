# DynamoDB Module for AI PPT Assistant
# Manages DynamoDB table for session state management

resource "aws_dynamodb_table" "sessions" {
  name         = "${var.project_name}-${var.environment}-sessions"
  billing_mode = var.billing_mode # On-demand billing as per spec
  hash_key     = "session_id"

  # Session ID attribute
  attribute {
    name = "session_id"
    type = "S"
  }

  # User ID attribute for GSI
  attribute {
    name = "user_id"
    type = "S"
  }

  # Timestamp attribute for GSI
  attribute {
    name = "created_at"
    type = "S"
  }

  # Global Secondary Index for querying by user_id
  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # TTL configuration - 30 days as per spec
  ttl {
    attribute_name = var.ttl_attribute
    enabled        = var.ttl_enabled
  }

  # Encryption at rest
  server_side_encryption {
    enabled = true
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-sessions"
      Description = "Session state management for AI PPT Assistant"
    }
  )
}

# DynamoDB table for task tracking (optional)
resource "aws_dynamodb_table" "tasks" {
  count = var.create_tasks_table ? 1 : 0

  name         = "${var.project_name}-${var.environment}-tasks"
  billing_mode = var.billing_mode
  hash_key     = "task_id"

  attribute {
    name = "task_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # GSI for querying by user_id
  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  # GSI for querying by status
  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    projection_type = "ALL"
  }

  # TTL for task cleanup
  ttl {
    attribute_name = "expiry"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-tasks"
      Description = "Task tracking for AI PPT Assistant"
    }
  )
}

# Checkpoints Table for checkpoint/recovery functionality
resource "aws_dynamodb_table" "checkpoints" {
  name         = "${var.project_name}-${var.environment}-checkpoints"
  billing_mode = var.billing_mode
  hash_key     = "checkpoint_id"

  attribute {
    name = "checkpoint_id"
    type = "S"
  }

  attribute {
    name = "task_id"
    type = "S"
  }

  attribute {
    name = "presentation_id"
    type = "S"
  }

  # Global Secondary Index for querying by task_id
  global_secondary_index {
    name            = "TaskIdIndex"
    hash_key        = "task_id"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by presentation_id
  global_secondary_index {
    name            = "PresentationIdIndex"
    hash_key        = "presentation_id"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Server-side encryption
  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-checkpoints"
    Type = "Checkpoints"
  })
}
