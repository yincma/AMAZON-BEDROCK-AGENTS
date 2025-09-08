# =============================================================================
# LAMBDA PERFORMANCE OPTIMIZATION CONFIGURATION
# =============================================================================
# This file contains performance optimization settings for Lambda functions
# to minimize cold start latency and improve overall system responsiveness.

# Performance optimization variables for the Lambda module
locals {
  # Enable performance optimizations
  enable_provisioned_concurrency = true
  
  # Provisioned concurrency settings based on expected traffic patterns
  # These values are optimized for production workloads
  provisioned_concurrency_config = {
    api_presentation_status = {
      provisioned_concurrent_executions = 5  # High frequency status checks
      qualifier                         = "$LATEST"
    }
    api_generate_presentation = {
      provisioned_concurrent_executions = 3  # Medium frequency new presentations
      qualifier                         = "$LATEST"
    }
    api_presentation_download = {
      provisioned_concurrent_executions = 2  # Lower frequency downloads
      qualifier                         = "$LATEST"
    }
    api_modify_slide = {
      provisioned_concurrent_executions = 2  # Lower frequency modifications
      qualifier                         = "$LATEST"
    }
  }
  
  # Lambda layer optimization configuration
  layer_optimization = {
    # Minimal layer for API functions to reduce cold start time
    minimal_layer = {
      name = "minimal-deps"
      size_limit_mb = 10  # Target: Keep under 10MB for fast cold starts
      functions = [
        "api_presentation_status",
        "api_presentation_download",
        "api_generate_presentation",
        "api_modify_slide",
        "find_image"  # Search operations benefit from fast cold start
      ]
    }
    
    # Content processing layer for controller functions
    content_layer = {
      name = "content-deps"
      size_limit_mb = 25  # Target: Keep under 25MB for reasonable cold starts
      functions = [
        "create_outline",
        "generate_content",
        "generate_image", 
        "generate_speaker_notes",
        "compile_pptx"
      ]
    }
  }
  
  # Memory optimization based on function workload
  memory_optimization = {
    # API functions: Fast response, minimal memory
    api_functions = {
      memory_mb = 512
      timeout_seconds = 10
    }
    
    # Light processing functions
    light_processing = {
      memory_mb = 768
      timeout_seconds = 30
    }
    
    # Medium processing functions  
    medium_processing = {
      memory_mb = 1536
      timeout_seconds = 60
    }
    
    # Heavy processing functions
    heavy_processing = {
      memory_mb = 2048
      timeout_seconds = 120
    }
    
    # Maximum processing (PPTX compilation)
    max_processing = {
      memory_mb = 3008
      timeout_seconds = 180
    }
  }
  
  # CloudWatch alarms thresholds for performance monitoring
  performance_thresholds = {
    cold_start_duration_ms = 1000    # Alert if cold start > 1 second
    error_count_5min = 5             # Alert if > 5 errors in 5 minutes
    timeout_percentage = 1           # Alert if > 1% of invocations timeout
    throttle_count = 1               # Alert on any throttling
  }
}

# Performance monitoring dashboard
resource "aws_cloudwatch_dashboard" "lambda_performance" {
  dashboard_name = "${var.project_name}-lambda-performance"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-api-presentation-status"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-api-generate-presentation"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-api-presentation-download"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-api-modify-slide"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Function Duration (ms)"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", "${var.project_name}-api-presentation-status"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.project_name}-api-generate-presentation"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.project_name}-api-presentation-download"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.project_name}-api-modify-slide"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Function Errors"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.project_name}-api-presentation-status"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.project_name}-api-generate-presentation"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.project_name}-api-presentation-download"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.project_name}-api-modify-slide"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Concurrent Executions"
          period  = 300
        }
      }
    ]
  })

}

# Output performance configuration for reference
output "performance_config" {
  description = "Lambda performance optimization configuration"
  value = {
    provisioned_concurrency_enabled = local.enable_provisioned_concurrency
    provisioned_concurrency_config  = local.provisioned_concurrency_config
    layer_optimization              = local.layer_optimization
    memory_optimization             = local.memory_optimization
    performance_thresholds          = local.performance_thresholds
    dashboard_name                  = aws_cloudwatch_dashboard.lambda_performance.dashboard_name
  }
}