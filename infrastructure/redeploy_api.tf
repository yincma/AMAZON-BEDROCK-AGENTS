# Force API Gateway redeployment
# Note: stage_name removed as it's deprecated. Stage is managed by aws_api_gateway_stage resource.
resource "aws_api_gateway_deployment" "force_redeploy" {
  rest_api_id = module.api_gateway.rest_api_id
  
  triggers = {
    redeployment = timestamp()
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_resource.templates,
    aws_api_gateway_resource.tasks,
    aws_api_gateway_method.get_templates,
    aws_api_gateway_method.get_task,
    aws_api_gateway_integration.get_templates,
    aws_api_gateway_integration.get_task,
    aws_lambda_function.list_presentations,
    aws_api_gateway_integration.list_presentations_fixed
  ]
}