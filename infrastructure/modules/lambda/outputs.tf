# Lambda Module Outputs

output "function_names" {
  description = "Map of Lambda function names"
  value = {
    create_outline         = try(aws_lambda_function.create_outline.function_name, "")
    generate_content       = try(aws_lambda_function.generate_content.function_name, "")
    generate_image         = try(aws_lambda_function.generate_image.function_name, "")
    find_image             = try(aws_lambda_function.find_image.function_name, "")
    generate_speaker_notes = try(aws_lambda_function.generate_speaker_notes.function_name, "")
    compile_pptx           = try(aws_lambda_function.compile_pptx.function_name, "")
    generate_presentation  = try(aws_lambda_function.api_generate_presentation.function_name, "")
    presentation_status    = try(aws_lambda_function.api_presentation_status.function_name, "")
    presentation_download  = try(aws_lambda_function.api_presentation_download.function_name, "")
    modify_slide           = try(aws_lambda_function.api_modify_slide.function_name, "")
  }
}

output "function_arns" {
  description = "Map of Lambda function ARNs"
  value = {
    create_outline         = try(aws_lambda_function.create_outline.arn, "")
    generate_content       = try(aws_lambda_function.generate_content.arn, "")
    generate_image         = try(aws_lambda_function.generate_image.arn, "")
    find_image             = try(aws_lambda_function.find_image.arn, "")
    generate_speaker_notes = try(aws_lambda_function.generate_speaker_notes.arn, "")
    compile_pptx           = try(aws_lambda_function.compile_pptx.arn, "")
    generate_presentation  = try(aws_lambda_function.api_generate_presentation.arn, "")
    presentation_status    = try(aws_lambda_function.api_presentation_status.arn, "")
    presentation_download  = try(aws_lambda_function.api_presentation_download.arn, "")
    modify_slide           = try(aws_lambda_function.api_modify_slide.arn, "")
  }
}

output "function_invoke_arns" {
  description = "Map of Lambda function invoke ARNs"
  value = {
    create_outline         = try(aws_lambda_function.create_outline.invoke_arn, "")
    generate_content       = try(aws_lambda_function.generate_content.invoke_arn, "")
    generate_image         = try(aws_lambda_function.generate_image.invoke_arn, "")
    find_image             = try(aws_lambda_function.find_image.invoke_arn, "")
    generate_speaker_notes = try(aws_lambda_function.generate_speaker_notes.invoke_arn, "")
    compile_pptx           = try(aws_lambda_function.compile_pptx.invoke_arn, "")
    generate_presentation  = try(aws_lambda_function.api_generate_presentation.invoke_arn, "")
    presentation_status    = try(aws_lambda_function.api_presentation_status.invoke_arn, "")
    presentation_download  = try(aws_lambda_function.api_presentation_download.invoke_arn, "")
    modify_slide           = try(aws_lambda_function.api_modify_slide.invoke_arn, "")
  }
}