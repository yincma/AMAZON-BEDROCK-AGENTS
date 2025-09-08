# API Gateway Module Outputs - AI PPT Assistant

# REST API Outputs
output "rest_api_id" {
  description = "The ID of the REST API"
  value       = aws_api_gateway_rest_api.main.id
}

output "api_id" {
  description = "The ID of the REST API (alias for rest_api_id)"
  value       = aws_api_gateway_rest_api.main.id
}

output "rest_api_arn" {
  description = "The ARN of the REST API"
  value       = aws_api_gateway_rest_api.main.arn
}

output "api_arn" {
  description = "The ARN of the REST API (alias for rest_api_arn)"
  value       = aws_api_gateway_rest_api.main.arn
}

output "rest_api_name" {
  description = "The name of the REST API"
  value       = aws_api_gateway_rest_api.main.name
}

output "rest_api_root_resource_id" {
  description = "The root resource ID of the REST API"
  value       = aws_api_gateway_rest_api.main.root_resource_id
}

# Stage and Deployment Outputs
output "stage_name" {
  description = "The name of the API Gateway stage"
  value       = var.create_deployment ? aws_api_gateway_stage.main[0].stage_name : var.stage_name
}

output "stage_arn" {
  description = "The ARN of the API Gateway stage"
  value       = var.create_deployment ? aws_api_gateway_stage.main[0].arn : null
}

output "deployment_id" {
  description = "The ID of the API Gateway deployment"
  value       = var.create_deployment ? aws_api_gateway_deployment.main[0].id : var.external_deployment_id
}

# 添加一个标志输出
output "deployment_managed_externally" {
  description = "Whether deployment is managed outside the module"
  value       = !var.create_deployment
}

output "invoke_url" {
  description = "The URL to invoke the API"
  value       = var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"
}

output "api_url" {
  description = "The URL to invoke the API (alias for invoke_url)"
  value       = var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"
}

output "execution_arn" {
  description = "The execution ARN for Lambda integration"
  value       = aws_api_gateway_rest_api.main.execution_arn
}

# API Key and Usage Plan Outputs
output "api_key_id" {
  description = "The ID of the API key"
  value       = try(aws_api_gateway_api_key.main[0].id, null)
}

output "api_key_value" {
  description = "The value of the API key"
  value       = try(aws_api_gateway_api_key.main[0].value, null)
  sensitive   = true
}

output "usage_plan_id" {
  description = "The ID of the usage plan"
  value       = try(aws_api_gateway_usage_plan.main[0].id, null)
}

output "usage_plan_name" {
  description = "The name of the usage plan"
  value       = try(aws_api_gateway_usage_plan.main[0].name, null)
}

# Resource IDs for Lambda Integration
output "resource_ids" {
  description = "Map of API Gateway resource IDs"
  value = {
    presentations   = aws_api_gateway_resource.presentations.id
    presentation_id = aws_api_gateway_resource.presentation_id.id
    sessions        = aws_api_gateway_resource.sessions.id
    session_id      = aws_api_gateway_resource.session_id.id
    agents          = aws_api_gateway_resource.agents.id
    agent_name      = aws_api_gateway_resource.agent_name.id
    agent_execute   = aws_api_gateway_resource.agent_execute.id
  }
}

# Resource Paths
output "resource_paths" {
  description = "Map of API Gateway resource paths"
  value = {
    presentations   = aws_api_gateway_resource.presentations.path
    presentation_id = aws_api_gateway_resource.presentation_id.path
    sessions        = aws_api_gateway_resource.sessions.path
    session_id      = aws_api_gateway_resource.session_id.path
    agents          = aws_api_gateway_resource.agents.path
    agent_execute   = aws_api_gateway_resource.agent_execute.path
  }
}

# Method Configuration
output "methods" {
  description = "Map of API Gateway method configurations"
  value = {
    create_presentation = {
      resource_id      = aws_api_gateway_method.create_presentation.resource_id
      http_method      = aws_api_gateway_method.create_presentation.http_method
      api_key_required = aws_api_gateway_method.create_presentation.api_key_required
    }
    get_presentation = {
      resource_id      = aws_api_gateway_method.get_presentation.resource_id
      http_method      = aws_api_gateway_method.get_presentation.http_method
      api_key_required = aws_api_gateway_method.get_presentation.api_key_required
    }
    list_presentations = {
      resource_id      = aws_api_gateway_method.list_presentations.resource_id
      http_method      = aws_api_gateway_method.list_presentations.http_method
      api_key_required = aws_api_gateway_method.list_presentations.api_key_required
    }
    create_session = {
      resource_id      = aws_api_gateway_method.create_session.resource_id
      http_method      = aws_api_gateway_method.create_session.http_method
      api_key_required = aws_api_gateway_method.create_session.api_key_required
    }
    get_session = {
      resource_id      = aws_api_gateway_method.get_session.resource_id
      http_method      = aws_api_gateway_method.get_session.http_method
      api_key_required = aws_api_gateway_method.get_session.api_key_required
    }
    execute_agent = {
      resource_id      = aws_api_gateway_method.execute_agent.resource_id
      http_method      = aws_api_gateway_method.execute_agent.http_method
      api_key_required = aws_api_gateway_method.execute_agent.api_key_required
    }
  }
}

# CloudWatch Logging
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.arn
}

# Endpoint Configuration
output "endpoint_configuration" {
  description = "The endpoint configuration of the REST API"
  value = {
    types            = aws_api_gateway_rest_api.main.endpoint_configuration[0].types
    vpc_endpoint_ids = try(aws_api_gateway_rest_api.main.endpoint_configuration[0].vpc_endpoint_ids, [])
  }
}

# API Endpoints (Full URLs)
output "api_endpoints" {
  description = "Full URLs for API endpoints"
  value = {
    presentations = {
      create = "${var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"}/presentations"
      list   = "${var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"}/presentations"
      get    = "${var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"}/presentations/{id}"
    }
    sessions = {
      create = "${var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"}/sessions"
      get    = "${var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"}/sessions/{id}"
    }
    agents = {
      execute = "${var.create_deployment ? aws_api_gateway_stage.main[0].invoke_url : "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"}/agents/{name}/execute"
    }
  }
}

# Throttle Settings
output "throttle_settings" {
  description = "API throttle settings"
  value = {
    rate_limit  = var.throttle_rate_limit
    burst_limit = var.throttle_burst_limit
  }
}

# Quota Settings
output "quota_settings" {
  description = "API quota settings"
  value = {
    limit  = var.quota_limit
    period = var.quota_period
  }
}

# Request Validators
output "request_validators" {
  description = "Request validator IDs"
  value = {
    validate_body   = aws_api_gateway_request_validator.validate_body.id
    validate_params = aws_api_gateway_request_validator.validate_params.id
    validate_all    = aws_api_gateway_request_validator.validate_all.id
  }
}

# Integration Information (for Lambda functions to use)
output "integration_config" {
  description = "Configuration for Lambda integrations"
  value = {
    rest_api_id   = aws_api_gateway_rest_api.main.id
    execution_arn = aws_api_gateway_rest_api.main.execution_arn
    stage_name    = var.create_deployment ? aws_api_gateway_stage.main[0].stage_name : var.stage_name
    resource_ids = {
      presentations   = aws_api_gateway_resource.presentations.id
      presentation_id = aws_api_gateway_resource.presentation_id.id
      sessions        = aws_api_gateway_resource.sessions.id
      session_id      = aws_api_gateway_resource.session_id.id
      agent_execute   = aws_api_gateway_resource.agent_execute.id
    }
  }
}

# Module Metadata
output "module_metadata" {
  description = "Module configuration metadata"
  value = {
    environment      = var.environment
    project_name     = var.project_name
    api_key_required = var.api_key_required
    xray_enabled     = var.enable_xray_tracing
    detailed_metrics = var.enable_detailed_metrics
    endpoint_type    = var.endpoint_type
    created_at       = timestamp()
  }
}