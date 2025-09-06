# S3 Module for AI PPT Assistant
# Manages S3 buckets for presentation storage

resource "aws_s3_bucket" "presentations" {
  bucket = "${var.project_name}-${var.environment}-presentations-${data.aws_caller_identity.current.account_id}"
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-presentations"
      Description = "Storage for AI-generated presentations"
    }
  )
}

# Server-side encryption (SSE-S3 as per spec)
resource "aws_s3_bucket_server_side_encryption_configuration" "presentations" {
  bucket = aws_s3_bucket.presentations.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versioning
resource "aws_s3_bucket_versioning" "presentations" {
  bucket = aws_s3_bucket.presentations.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle rules - 30 days to IA storage as per design doc
resource "aws_s3_bucket_lifecycle_configuration" "presentations" {
  bucket = aws_s3_bucket.presentations.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Public access block
resource "aws_s3_bucket_public_access_block" "presentations" {
  bucket = aws_s3_bucket.presentations.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for presigned URLs
resource "aws_s3_bucket_cors_configuration" "presentations" {
  bucket = aws_s3_bucket.presentations.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT", "POST"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# Data source for account ID
data "aws_caller_identity" "current" {}
