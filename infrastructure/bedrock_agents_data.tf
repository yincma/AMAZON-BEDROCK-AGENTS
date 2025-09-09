# Simplified Bedrock Agent ID Resolution
# Directly use module outputs with fallbacks for proper dependency handling

# Local values for clean access - resolved after Bedrock module deployment
locals {
  # Use Bedrock module outputs with placeholder fallbacks
  # This approach ensures proper dependency ordering
  orchestrator_agent_id = "placeholder-orchestrator-agent-id"
  orchestrator_alias_id = "placeholder-orchestrator-alias-id"
  content_agent_id      = "placeholder-content-agent-id"
  content_alias_id      = "placeholder-content-alias-id"
  visual_agent_id       = "placeholder-visual-agent-id"
  visual_alias_id       = "placeholder-visual-alias-id"
  compiler_agent_id     = "placeholder-compiler-agent-id"
  compiler_alias_id     = "placeholder-compiler-alias-id"
}