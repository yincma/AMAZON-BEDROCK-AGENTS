#!/bin/bash
# Sync Bedrock Agent configuration to Lambda functions
# This script ensures all Lambda functions have the correct Bedrock Agent IDs and Alias IDs

set -e

echo "🔄 Starting Bedrock configuration sync..."

# Get Bedrock Agent IDs and Alias IDs
get_agent_info() {
    local agent_name=$1
    local agent_id=$(aws bedrock-agent list-agents \
        --query "agentSummaries[?contains(agentName, '${agent_name}')].agentId | [0]" \
        --output text --region us-east-1 2>/dev/null)
    
    if [ "$agent_id" != "None" ] && [ -n "$agent_id" ]; then
        local alias_id=$(aws bedrock-agent list-agent-aliases \
            --agent-id "$agent_id" \
            --query "agentAliasSummaries[?agentAliasName=='production'].agentAliasId | [0]" \
            --output text --region us-east-1 2>/dev/null)
        
        if [ "$alias_id" == "None" ]; then
            # If no 'production' alias, get the first available alias
            alias_id=$(aws bedrock-agent list-agent-aliases \
                --agent-id "$agent_id" \
                --query "agentAliasSummaries[0].agentAliasId" \
                --output text --region us-east-1 2>/dev/null)
        fi
        
        echo "${agent_id}:${alias_id}"
    else
        echo "NOT_FOUND:NOT_FOUND"
    fi
}

# Get all agent configurations
echo "📊 Fetching Bedrock Agent configurations..."
ORCHESTRATOR_INFO=$(get_agent_info "orchestrator")
CONTENT_INFO=$(get_agent_info "content")
VISUAL_INFO=$(get_agent_info "visual")
COMPILER_INFO=$(get_agent_info "compiler")

# Parse the results
IFS=':' read -r ORCHESTRATOR_ID ORCHESTRATOR_ALIAS <<< "$ORCHESTRATOR_INFO"
IFS=':' read -r CONTENT_ID CONTENT_ALIAS <<< "$CONTENT_INFO"
IFS=':' read -r VISUAL_ID VISUAL_ALIAS <<< "$VISUAL_INFO"
IFS=':' read -r COMPILER_ID COMPILER_ALIAS <<< "$COMPILER_INFO"

echo "✅ Found Bedrock Agents:"
echo "  - Orchestrator: ID=$ORCHESTRATOR_ID, Alias=$ORCHESTRATOR_ALIAS"
echo "  - Content: ID=$CONTENT_ID, Alias=$CONTENT_ALIAS"
echo "  - Visual: ID=$VISUAL_ID, Alias=$VISUAL_ALIAS"
echo "  - Compiler: ID=$COMPILER_ID, Alias=$COMPILER_ALIAS"

# Get S3 bucket name
S3_BUCKET=$(aws s3 ls | grep 'ai-ppt-assistant-dev-presentations' | awk '{print $3}' | head -1)
if [ -z "$S3_BUCKET" ]; then
    S3_BUCKET="ai-ppt-assistant-dev-presentations-375004070918"
fi

echo "🪣 S3 Bucket: $S3_BUCKET"

# Update Lambda functions
update_lambda_env() {
    local func_name=$1
    local dynamodb_table=$2
    
    echo "  Updating $func_name..."
    
    aws lambda update-function-configuration \
        --function-name "$func_name" \
        --environment Variables="{
            S3_BUCKET=$S3_BUCKET,
            DYNAMODB_TABLE=$dynamodb_table,
            TASKS_TABLE=ai-ppt-assistant-dev-tasks,
            CHECKPOINTS_TABLE=ai-ppt-assistant-dev-checkpoints,
            SESSIONS_TABLE=ai-ppt-assistant-dev-sessions,
            ORCHESTRATOR_AGENT_ID=$ORCHESTRATOR_ID,
            ORCHESTRATOR_ALIAS_ID=$ORCHESTRATOR_ALIAS,
            CONTENT_AGENT_ID=$CONTENT_ID,
            CONTENT_ALIAS_ID=$CONTENT_ALIAS,
            VISUAL_AGENT_ID=$VISUAL_ID,
            VISUAL_ALIAS_ID=$VISUAL_ALIAS,
            COMPILER_AGENT_ID=$COMPILER_ID,
            COMPILER_ALIAS_ID=$COMPILER_ALIAS,
            SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/375004070918/ai-ppt-assistant-dev-tasks,
            BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-20250514-v1:0,
            BEDROCK_ORCHESTRATOR_MODEL_ID=us.anthropic.claude-opus-4-1-20250805-v1:0,
            NOVA_MODEL_ID=amazon.nova-canvas-v1:0,
            LOG_LEVEL=INFO
        }" \
        --region us-east-1 > /dev/null 2>&1 && echo "    ✅ Success" || echo "    ⚠️ Update failed (function may not exist)"
}

echo ""
echo "🔧 Updating Lambda functions..."

# Update API Lambda functions
echo "📡 API Functions:"
update_lambda_env "ai-ppt-assistant-api-generate-presentation" "ai-ppt-assistant-dev-tasks"
update_lambda_env "ai-ppt-assistant-api-presentation-status" "ai-ppt-assistant-dev-sessions"
update_lambda_env "ai-ppt-assistant-api-presentation-download" "ai-ppt-assistant-dev-sessions"
update_lambda_env "ai-ppt-assistant-api-task-processor" "ai-ppt-assistant-dev-sessions"
update_lambda_env "ai-ppt-assistant-api-modify-slide" "ai-ppt-assistant-dev-tasks"

echo ""
echo "🎮 Controller Functions:"
# Update Controller Lambda functions
update_lambda_env "ai-ppt-assistant-create-outline" "ai-ppt-assistant-dev-tasks"
update_lambda_env "ai-ppt-assistant-generate-content" "ai-ppt-assistant-dev-tasks"
update_lambda_env "ai-ppt-assistant-generate-image" "ai-ppt-assistant-dev-tasks"
update_lambda_env "ai-ppt-assistant-compile-pptx" "ai-ppt-assistant-dev-tasks"
update_lambda_env "ai-ppt-assistant-generate-speaker-notes" "ai-ppt-assistant-dev-tasks"
update_lambda_env "ai-ppt-assistant-find-image" "ai-ppt-assistant-dev-tasks"

echo ""
echo "✅ Bedrock configuration sync completed!"
echo ""
echo "💡 Tip: Run 'python3 scripts/verify_deployment.py' to verify the configuration"
