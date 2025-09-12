# Bedrock Agents Module - All Bedrock Agents for AI PPT Assistant

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# IAM Role for Bedrock Agents
resource "aws_iam_role" "bedrock_agent_role" {
  for_each = var.agents

  name = "${var.project_name}-${each.key}-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Agent = each.key
  })
}

# IAM Policy for Bedrock Agents
resource "aws_iam_policy" "bedrock_agent_policy" {
  for_each = var.agents

  name        = "${var.project_name}-${each.key}-agent-policy"
  description = "Policy for ${each.key} Bedrock Agent"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${each.value.model_id}",
          "arn:aws:bedrock:*:*:inference-profile/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:GetInferenceProfile",
          "bedrock:ListInferenceProfiles", 
          "bedrock:UseInferenceProfile"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = values(var.lambda_function_arns[each.key])
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = var.dynamodb_table_arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "bedrock_agent_policy_attachment" {
  for_each = var.agents

  policy_arn = aws_iam_policy.bedrock_agent_policy[each.key].arn
  role       = aws_iam_role.bedrock_agent_role[each.key].name
}

# S3 Bucket for Agent configurations
resource "aws_s3_bucket" "agent_configs" {
  bucket = "${var.project_name}-bedrock-agent-configs"

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "agent_configs" {
  bucket = aws_s3_bucket.agent_configs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Upload agent configuration files to S3
resource "aws_s3_object" "agent_instructions" {
  for_each = var.agents

  bucket = aws_s3_bucket.agent_configs.id
  key    = "${each.key}/instructions.txt"
  source = "${path.module}/../../../agents/${each.key}/instructions.txt"
  etag   = filemd5("${path.module}/../../../agents/${each.key}/instructions.txt")

  tags = merge(var.tags, {
    Agent = each.key
  })
}

resource "aws_s3_object" "agent_action_groups" {
  for_each = var.agents

  bucket = aws_s3_bucket.agent_configs.id
  key    = "${each.key}/action_groups.json"
  source = "${path.module}/../../../agents/${each.key}/action_groups.json"
  etag   = filemd5("${path.module}/../../../agents/${each.key}/action_groups.json")

  tags = merge(var.tags, {
    Agent = each.key
  })
}

# Bedrock Agent: Orchestrator
resource "aws_bedrockagent_agent" "orchestrator" {
  agent_name                  = "${var.project_name}-orchestrator-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent_role["orchestrator"].arn
  foundation_model            = var.agents["orchestrator"].model_id
  idle_session_ttl_in_seconds = 600
  description                 = "Master orchestrator agent for AI PPT Assistant"

  instruction = file("${path.module}/../../../agents/orchestrator/instructions.txt")

# Removed prompt_override_configuration to use default Bedrock Agent prompts
  # Custom inference configuration is not compatible with DEFAULT prompt creation mode

  tags = merge(var.tags, {
    Agent = "orchestrator"
  })
}

# Bedrock Agent: Content
resource "aws_bedrockagent_agent" "content" {
  agent_name                  = "${var.project_name}-content-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent_role["content"].arn
  foundation_model            = var.agents["content"].model_id
  idle_session_ttl_in_seconds = 600
  description                 = "Content generation agent for presentations"

  instruction = file("${path.module}/../../../agents/content/instructions.txt")

# Removed prompt_override_configuration to use default Bedrock Agent prompts
  # Custom inference configuration is not compatible with DEFAULT prompt creation mode

  tags = merge(var.tags, {
    Agent = "content"
  })
}

# Bedrock Agent: Visual
resource "aws_bedrockagent_agent" "visual" {
  agent_name                  = "${var.project_name}-visual-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent_role["visual"].arn
  foundation_model            = var.agents["visual"].model_id
  idle_session_ttl_in_seconds = 600
  description                 = "Visual generation agent for presentations"

  instruction = file("${path.module}/../../../agents/visual/instructions.txt")

# Removed prompt_override_configuration to use default Bedrock Agent prompts
  # Custom inference configuration is not compatible with DEFAULT prompt creation mode

  tags = merge(var.tags, {
    Agent = "visual"
  })
}

# Bedrock Agent: Compiler
resource "aws_bedrockagent_agent" "compiler" {
  agent_name                  = "${var.project_name}-compiler-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent_role["compiler"].arn
  foundation_model            = var.agents["compiler"].model_id
  idle_session_ttl_in_seconds = 600
  description                 = "File compilation agent for presentations"

  instruction = file("${path.module}/../../../agents/compiler/instructions.txt")

# Removed prompt_override_configuration to use default Bedrock Agent prompts
  # Custom inference configuration is not compatible with DEFAULT prompt creation mode

  tags = merge(var.tags, {
    Agent = "compiler"
  })
}

# Agent Aliases for stable endpoints
resource "aws_bedrockagent_agent_alias" "orchestrator" {
  agent_alias_name = "production"
  agent_id         = aws_bedrockagent_agent.orchestrator.id
  description      = "Production alias for Orchestrator Agent"

  tags = merge(var.tags, {
    Agent = "orchestrator"
  })
}

resource "aws_bedrockagent_agent_alias" "content" {
  agent_alias_name = "production"
  agent_id         = aws_bedrockagent_agent.content.id
  description      = "Production alias for Content Agent"

  tags = merge(var.tags, {
    Agent = "content"
  })
}

resource "aws_bedrockagent_agent_alias" "visual" {
  agent_alias_name = "production"
  agent_id         = aws_bedrockagent_agent.visual.id
  description      = "Production alias for Visual Agent"

  tags = merge(var.tags, {
    Agent = "visual"
  })
}

resource "aws_bedrockagent_agent_alias" "compiler" {
  agent_alias_name = "production"
  agent_id         = aws_bedrockagent_agent.compiler.id
  description      = "Production alias for Compiler Agent"

  tags = merge(var.tags, {
    Agent = "compiler"
  })
}

# Action Groups for each agent - Temporarily disabled for deployment
# TODO: Fix OpenAPI 3.0 specification format and re-enable

/*
resource "aws_bedrockagent_agent_action_group" "orchestrator_actions" {
  agent_id                   = aws_bedrockagent_agent.orchestrator.id
  agent_version              = "DRAFT"
  action_group_name          = "PresentationManagement"
  description                = "Manages presentation lifecycle"
  skip_resource_in_use_check = true

  action_group_executor {
    lambda = var.lambda_function_arns["orchestrator"]["create_outline"]
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_configs.id
      s3_object_key  = aws_s3_object.agent_action_groups["orchestrator"].key
    }
  }
}

resource "aws_bedrockagent_agent_action_group" "content_actions" {
  agent_id                   = aws_bedrockagent_agent.content.id
  agent_version              = "DRAFT"
  action_group_name          = "ContentGeneration"
  description                = "Generates presentation content"
  skip_resource_in_use_check = true

  action_group_executor {
    lambda = var.lambda_function_arns["content"]["generate_content"]
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_configs.id
      s3_object_key  = aws_s3_object.agent_action_groups["content"].key
    }
  }
}

resource "aws_bedrockagent_agent_action_group" "visual_actions" {
  agent_id                   = aws_bedrockagent_agent.visual.id
  agent_version              = "DRAFT"
  action_group_name          = "ImageGeneration"
  description                = "Generates visual elements"
  skip_resource_in_use_check = true

  action_group_executor {
    lambda = var.lambda_function_arns["visual"]["generate_image"]
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_configs.id
      s3_object_key  = aws_s3_object.agent_action_groups["visual"].key
    }
  }
}

resource "aws_bedrockagent_agent_action_group" "compiler_actions" {
  agent_id                   = aws_bedrockagent_agent.compiler.id
  agent_version              = "DRAFT"
  action_group_name          = "PresentationAssembly"
  description                = "Assembles final presentation files"
  skip_resource_in_use_check = true

  action_group_executor {
    lambda = var.lambda_function_arns["compiler"]["compile_pptx"]
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_configs.id
      s3_object_key  = aws_s3_object.agent_action_groups["compiler"].key
    }
  }
}
*/

# Outputs
output "agent_ids" {
  value = {
    orchestrator = aws_bedrockagent_agent.orchestrator.id
    content      = aws_bedrockagent_agent.content.id
    visual       = aws_bedrockagent_agent.visual.id
    compiler     = aws_bedrockagent_agent.compiler.id
  }
}

output "agent_alias_ids" {
  value = {
    orchestrator = aws_bedrockagent_agent_alias.orchestrator.agent_alias_id
    content      = aws_bedrockagent_agent_alias.content.agent_alias_id
    visual       = aws_bedrockagent_agent_alias.visual.agent_alias_id
    compiler     = aws_bedrockagent_agent_alias.compiler.agent_alias_id
  }
}

output "agent_role_arns" {
  value = {
    for k, v in aws_iam_role.bedrock_agent_role : k => v.arn
  }
}

output "config_bucket_name" {
  value = aws_s3_bucket.agent_configs.id
}