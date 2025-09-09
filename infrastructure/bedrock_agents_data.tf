# Bedrock Agents Dynamic Data Sources
# 动态获取已部署的Bedrock Agent IDs，避免硬编码

# Data source to get orchestrator agent
data "external" "orchestrator_agent" {
  program = ["bash", "-c", <<-EOF
    agent_name="ai-ppt-assistant-orchestrator-agent"
    agent_info=$(aws bedrock-agent list-agents --region us-east-1 --query "agentSummaries[?agentName=='$agent_name'] | [0]" --output json 2>/dev/null)
    
    if [[ "$agent_info" == "null" || -z "$agent_info" ]]; then
      echo '{"agent_id": "placeholder-orchestrator-agent-id", "alias_id": "placeholder-orchestrator-alias-id"}'
      exit 0
    fi
    
    agent_id=$(echo "$agent_info" | jq -r '.agentId // "placeholder-orchestrator-agent-id"')
    alias_info=$(aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --region us-east-1 --query 'agentAliasSummaries[0]' --output json 2>/dev/null)
    alias_id=$(echo "$alias_info" | jq -r '.agentAliasId // "placeholder-orchestrator-alias-id"')
    
    echo "{\"agent_id\": \"$agent_id\", \"alias_id\": \"$alias_id\"}"
EOF
  ]
}

# Data source to get content agent
data "external" "content_agent" {
  program = ["bash", "-c", <<-EOF
    agent_name="ai-ppt-assistant-content-agent"
    agent_info=$(aws bedrock-agent list-agents --region us-east-1 --query "agentSummaries[?agentName=='$agent_name'] | [0]" --output json 2>/dev/null)
    
    if [[ "$agent_info" == "null" || -z "$agent_info" ]]; then
      echo '{"agent_id": "placeholder-content-agent-id", "alias_id": "placeholder-content-alias-id"}'
      exit 0
    fi
    
    agent_id=$(echo "$agent_info" | jq -r '.agentId // "placeholder-content-agent-id"')
    alias_info=$(aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --region us-east-1 --query 'agentAliasSummaries[0]' --output json 2>/dev/null)
    alias_id=$(echo "$alias_info" | jq -r '.agentAliasId // "placeholder-content-alias-id"')
    
    echo "{\"agent_id\": \"$agent_id\", \"alias_id\": \"$alias_id\"}"
EOF
  ]
}

# Data source to get visual agent
data "external" "visual_agent" {
  program = ["bash", "-c", <<-EOF
    agent_name="ai-ppt-assistant-visual-agent"
    agent_info=$(aws bedrock-agent list-agents --region us-east-1 --query "agentSummaries[?agentName=='$agent_name'] | [0]" --output json 2>/dev/null)
    
    if [[ "$agent_info" == "null" || -z "$agent_info" ]]; then
      echo '{"agent_id": "placeholder-visual-agent-id", "alias_id": "placeholder-visual-alias-id"}'
      exit 0
    fi
    
    agent_id=$(echo "$agent_info" | jq -r '.agentId // "placeholder-visual-agent-id"')
    alias_info=$(aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --region us-east-1 --query 'agentAliasSummaries[0]' --output json 2>/dev/null)
    alias_id=$(echo "$alias_info" | jq -r '.agentAliasId // "placeholder-visual-alias-id"')
    
    echo "{\"agent_id\": \"$agent_id\", \"alias_id\": \"$alias_id\"}"
EOF
  ]
}

# Data source to get compiler agent
data "external" "compiler_agent" {
  program = ["bash", "-c", <<-EOF
    agent_name="ai-ppt-assistant-compiler-agent"
    agent_info=$(aws bedrock-agent list-agents --region us-east-1 --query "agentSummaries[?agentName=='$agent_name'] | [0]" --output json 2>/dev/null)
    
    if [[ "$agent_info" == "null" || -z "$agent_info" ]]; then
      echo '{"agent_id": "placeholder-compiler-agent-id", "alias_id": "placeholder-compiler-alias-id"}'
      exit 0
    fi
    
    agent_id=$(echo "$agent_info" | jq -r '.agentId // "placeholder-compiler-agent-id"')
    alias_info=$(aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --region us-east-1 --query 'agentAliasSummaries[0]' --output json 2>/dev/null)
    alias_id=$(echo "$alias_info" | jq -r '.agentAliasId // "placeholder-compiler-alias-id"')
    
    echo "{\"agent_id\": \"$agent_id\", \"alias_id\": \"$alias_id\"}"
EOF
  ]
}

# Local values for clean access
locals {
  orchestrator_agent_id = data.external.orchestrator_agent.result.agent_id
  orchestrator_alias_id = data.external.orchestrator_agent.result.alias_id
  content_agent_id      = data.external.content_agent.result.agent_id
  content_alias_id      = data.external.content_agent.result.alias_id
  visual_agent_id       = data.external.visual_agent.result.agent_id
  visual_alias_id       = data.external.visual_agent.result.alias_id
  compiler_agent_id     = data.external.compiler_agent.result.agent_id
  compiler_alias_id     = data.external.compiler_agent.result.alias_id
}