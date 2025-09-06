# PPT Orchestrator Agent

## Overview

The PPT Orchestrator Agent is the main coordination agent for the AI PPT Assistant system. It manages the entire presentation creation workflow by orchestrating between specialized agents and services.

## Architecture

```
User Request
     ↓
Orchestrator Agent
     ├── Content Generation
     │   ├── Create Outline
     │   ├── Generate Content
     │   └── Generate Speaker Notes
     │
     ├── Visual Generation
     │   ├── Find Images
     │   └── Generate Images
     │
     └── Compilation
         └── Compile PPTX
```

## Components

### 1. Agent Configuration (`agent_config.json`)
- **Model**: Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)
- **Session TTL**: 600 seconds
- **Memory**: Session-based memory for context retention
- **Temperature**: 0.7 for balanced creativity/consistency

### 2. Action Groups (`action_groups.json`)

#### PresentationManagement
- `createPresentation`: Initialize new presentation with topic and parameters
- `getPresentationStatus`: Check creation progress
- `listPresentations`: List all presentations in session

#### ContentGeneration
- `generateSlideContent`: Create detailed slide content
- `generateSpeakerNotes`: Generate time-allocated speaker notes
- `refineContent`: Modify existing content based on feedback

#### VisualGeneration
- `findOrGenerateImages`: Source images from multiple providers
- `generateChart`: Create data visualizations

#### PresentationCompilation
- `compilePresentation`: Assemble final PPTX file
- `downloadPresentation`: Get download URL
- `previewPresentation`: Generate slide previews

#### SessionManagement
- `createSession`: Initialize user session
- `updateSessionContext`: Update preferences
- `clearSession`: Reset session data

### 3. Knowledge Base (`knowledge_base.json`)

#### Data Sources
1. **Presentation Templates**: Professional, Creative, Minimalist, Technical styles
2. **Best Practices**: Structure guidelines, audience adaptation, timing rules
3. **Domain Knowledge**: Business, Technology, Education frameworks
4. **Visual Guidelines**: Chart selection, color theory, accessibility

#### Vector Configuration
- **Embedding Model**: Amazon Titan Embed Text v2
- **Dimensions**: 1024
- **Search Type**: Hybrid (keyword + semantic)
- **Storage**: OpenSearch Serverless

### 4. Prompt Templates (`prompt_templates.json`)

#### Templates
- `userQueryProcessing`: Extract requirements from natural language
- `workflowOrchestration`: Determine optimal workflow steps
- `qualityControl`: Validate presentation quality
- `errorRecovery`: Handle failures gracefully
- `sessionContext`: Maintain conversation continuity
- `responseGeneration`: Create user-friendly responses

## Deployment

### Prerequisites
1. AWS Account with Bedrock access
2. Lambda functions deployed (Task 1-13)
3. S3 buckets created
4. DynamoDB tables configured
5. IAM roles with appropriate permissions

### CloudFormation Deployment

```bash
# Deploy the orchestrator agent stack
aws cloudformation deploy \
  --stack-name ppt-orchestrator-agent \
  --template-file agents/orchestrator/cloudformation.yaml \
  --parameter-overrides \
    Environment=dev \
    BedrockAgentRoleArn=arn:aws:iam::ACCOUNT:role/bedrock-agent-role \
    CreateOutlineLambdaArn=arn:aws:lambda:REGION:ACCOUNT:function:create-outline \
    GenerateContentLambdaArn=arn:aws:lambda:REGION:ACCOUNT:function:generate-content \
    FindImageLambdaArn=arn:aws:lambda:REGION:ACCOUNT:function:find-image \
    GenerateSpeakerNotesLambdaArn=arn:aws:lambda:REGION:ACCOUNT:function:generate-speaker-notes \
    CompilePptxLambdaArn=arn:aws:lambda:REGION:ACCOUNT:function:compile-pptx \
    KnowledgeBaseBucketName=ppt-knowledge-base-bucket \
  --capabilities CAPABILITY_IAM
```

### Manual Configuration

If not using CloudFormation:

1. **Create Agent**:
```bash
aws bedrock-agent create-agent \
  --agent-name ppt-orchestrator-agent \
  --agent-resource-role-arn $ROLE_ARN \
  --foundation-model anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --instruction "$(cat agent_config.json | jq -r .instruction)"
```

2. **Add Action Groups**:
```bash
aws bedrock-agent create-agent-action-group \
  --agent-id $AGENT_ID \
  --action-group-name PresentationManagement \
  --action-group-executor '{"lambda": "'$LAMBDA_ARN'"}'
```

3. **Prepare Agent**:
```bash
aws bedrock-agent prepare-agent \
  --agent-id $AGENT_ID
```

4. **Create Alias**:
```bash
aws bedrock-agent create-agent-alias \
  --agent-id $AGENT_ID \
  --agent-alias-name prod-alias
```

## Usage Examples

### Create Presentation
```
User: "Create a 15-minute presentation about cloud computing for executives"

Orchestrator: 
1. Extracts requirements (topic: cloud computing, audience: executives, duration: 15 min)
2. Calls createPresentation → generates outline
3. Calls generateSlideContent → creates slide content
4. Calls findOrGenerateImages → sources visuals
5. Calls generateSpeakerNotes → creates timing notes
6. Calls compilePresentation → assembles PPTX
7. Returns download URL
```

### Modify Presentation
```
User: "Make the presentation more technical and add a cost comparison chart"

Orchestrator:
1. Retrieves current presentation context
2. Calls refineContent with technical focus
3. Calls generateChart for cost comparison
4. Calls compilePresentation with updates
5. Returns updated download URL
```

## Monitoring

### CloudWatch Metrics
- Agent invocations
- Success/failure rates
- Average response time
- Token usage per request

### Logs
- Agent conversation logs
- Lambda function logs
- Error traces

### Alarms
- High error rate (>5%)
- Response time (>30 seconds)
- Token usage spike

## Troubleshooting

### Common Issues

1. **Agent not responding**
   - Check IAM role permissions
   - Verify Lambda functions are accessible
   - Review CloudWatch logs

2. **Knowledge base not working**
   - Ensure S3 bucket has documents
   - Check OpenSearch collection status
   - Verify embedding model access

3. **Slow response times**
   - Check Lambda cold starts
   - Review token usage
   - Optimize prompt templates

4. **Error in workflow**
   - Check individual Lambda function logs
   - Verify S3/DynamoDB permissions
   - Review error recovery logic

## Best Practices

1. **Session Management**
   - Use session IDs consistently
   - Clear old sessions periodically
   - Store user preferences

2. **Error Handling**
   - Implement retry with exponential backoff
   - Provide clear error messages
   - Offer alternative actions

3. **Performance**
   - Cache frequently used templates
   - Parallelize independent operations
   - Optimize prompt lengths

4. **Quality Assurance**
   - Validate all user inputs
   - Check content coherence
   - Verify visual relevance

## Future Enhancements

- [ ] Multi-agent collaboration for complex presentations
- [ ] Real-time collaboration features
- [ ] Advanced analytics and insights
- [ ] Custom branding integration
- [ ] Video/animation support
- [ ] Export to additional formats (PDF, Google Slides)
- [ ] Presentation rehearsal mode
- [ ] Audience engagement analytics