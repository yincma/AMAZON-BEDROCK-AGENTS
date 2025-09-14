# AI PPT Assistant API Documentation

Welcome to the comprehensive API documentation for the AI PPT Assistant - a powerful service for creating AI-generated PowerPoint presentations using Amazon Bedrock models.

## Documentation Overview

This documentation suite provides everything you need to integrate with the AI PPT Assistant API:

### 📋 [API Reference](./API_REFERENCE.md)
Complete reference documentation covering all endpoints, parameters, and responses. Includes:
- Detailed endpoint descriptions
- Request/response examples
- Authentication methods
- Rate limiting information
- Python, JavaScript, and cURL examples

### 📝 [OpenAPI Specification](./openapi-v1.yaml)
Machine-readable OpenAPI 3.1 specification that can be used to:
- Generate client SDKs in any language
- Import into API testing tools
- Set up API mocking and testing
- Generate interactive documentation

### ❌ [Error Codes Reference](./ERROR_CODES.md)
Comprehensive error handling guide including:
- All error codes and their meanings
- Common causes and solutions
- Error response formats
- Best practices for error handling
- Troubleshooting guide

### 💡 [Usage Examples](./EXAMPLES.md)
Extensive code examples and integration patterns:
- Basic workflows
- Advanced use cases
- Complete integration examples
- Async/batch processing
- Error handling patterns
- Custom SDK implementations

### 🔧 [Postman Collection](./postman-collection.json)
Ready-to-use Postman collection featuring:
- All API endpoints with examples
- Automated tests
- Environment variable setup
- Complete workflow examples
- Error scenario testing

## Quick Start

### 1. Get Your API Key
Sign up at [AI PPT Assistant](https://ai-ppt-assistant.com) to get your API key.

### 2. Make Your First Request
```bash
curl -X POST https://api.ai-ppt-assistant.com/v1/presentations/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "topic": "Introduction to Machine Learning",
    "page_count": 8,
    "style": "professional"
  }'
```

### 3. Check Status and Download
```bash
# Check status (use presentation_id from step 2)
curl -X GET https://api.ai-ppt-assistant.com/v1/presentations/{id}/status \
  -H "X-API-Key: your-api-key-here"

# Download when completed
curl -X GET https://api.ai-ppt-assistant.com/v1/presentations/{id}/download \
  -H "X-API-Key: your-api-key-here"
```

## API Overview

### Base URLs
- **Production**: `https://api.ai-ppt-assistant.com/v1`
- **Staging**: `https://staging-api.ai-ppt-assistant.com/v1`
- **Development**: `https://dev-api.ai-ppt-assistant.com/v1`

### Authentication
Two methods supported:
- **API Key**: Include `X-API-Key: your-key` header
- **Bearer Token**: Include `Authorization: Bearer your-jwt-token` header

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/presentations/generate` | POST | Generate new presentation |
| `/presentations/{id}/status` | GET | Check generation status |
| `/presentations/{id}/download` | GET | Get download URL |
| `/presentations/{id}/slides/{n}` | PATCH | Update slide content |
| `/presentations/{id}/slides/{n}/image` | POST | Regenerate slide image |
| `/presentations/{id}/regenerate` | POST | Regenerate content |
| `/presentations/{id}` | DELETE | Delete presentation |
| `/tasks/{id}/status` | GET | Check task status |
| `/health` | GET | System health check |

### Rate Limits
- Generate Presentation: 10/min
- Status Checks: 60/min
- Slide Updates: 30/min
- Image Generation: 5/min

## Features

### 🤖 AI-Powered Generation
- Create presentations on any topic
- Multiple styles: professional, creative, minimal, academic, business
- Multi-language support (10+ languages)
- Audience-specific content optimization

### 📊 Advanced Customization
- Individual slide editing
- Custom layouts and styling
- AI image generation and regeneration
- Speaker notes management
- Style override capabilities

### 🔄 Flexible Workflows
- Asynchronous processing
- Real-time progress tracking
- Batch operations support
- Partial regeneration
- Version control with ETags

### 🛡️ Production Ready
- Comprehensive error handling
- Rate limiting and quotas
- Health monitoring
- Request/response validation
- Security best practices

## Integration Examples

### Python
```python
import requests

client = requests.Session()
client.headers.update({
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
})

# Generate presentation
response = client.post(
    "https://api.ai-ppt-assistant.com/v1/presentations/generate",
    json={
        "topic": "Machine Learning Basics",
        "page_count": 10,
        "style": "professional"
    }
)

presentation_id = response.json()["presentation_id"]
print(f"Generation started: {presentation_id}")
```

### JavaScript
```javascript
const response = await fetch('https://api.ai-ppt-assistant.com/v1/presentations/generate', {
    method: 'POST',
    headers: {
        'X-API-Key': 'your-api-key',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        topic: 'Machine Learning Basics',
        page_count: 10,
        style: 'professional'
    })
});

const data = await response.json();
console.log(`Generation started: ${data.presentation_id}`);
```

## Support and Resources

### 📚 Additional Resources
- [OpenAPI Specification](./openapi-v1.yaml) - Machine-readable API spec
- [Postman Collection](./postman-collection.json) - Import into Postman for testing
- [GitHub Repository](https://github.com/ai-ppt-assistant/api-examples) - Code examples and SDKs

### 🆘 Getting Help
- **Email Support**: support@ai-ppt-assistant.com
- **Documentation**: https://docs.ai-ppt-assistant.com
- **Status Page**: https://status.ai-ppt-assistant.com
- **Community**: https://community.ai-ppt-assistant.com

### 🚨 Enterprise Support
- **Priority Support**: enterprise@ai-ppt-assistant.com
- **Custom Integrations**: solutions@ai-ppt-assistant.com
- **SLA Options**: Available for enterprise customers

## Version History

- **v1.0.0** (Current) - Initial production release
  - All core endpoints
  - Full CRUD operations
  - Async task management
  - Comprehensive error handling

## Best Practices

### 🔐 Security
- Store API keys securely (environment variables)
- Use HTTPS for all requests
- Implement proper error handling
- Validate all user inputs

### ⚡ Performance
- Implement exponential backoff for retries
- Cache responses when appropriate
- Use appropriate timeout values
- Monitor rate limits

### 🔄 Reliability
- Handle all error scenarios
- Implement circuit breakers for production
- Log requests and responses for debugging
- Set up monitoring and alerting

### 💾 Data Management
- Clean up unused presentations
- Monitor storage usage
- Implement data retention policies
- Use appropriate backup strategies

## Contributing

We welcome feedback and contributions to improve our API documentation:

1. **Report Issues**: Found a bug or unclear documentation? [Create an issue](mailto:support@ai-ppt-assistant.com)
2. **Suggest Improvements**: Have ideas for better examples or documentation? We'd love to hear them!
3. **Share Use Cases**: Help us improve by sharing how you're using the API

---

**Last Updated**: January 2024
**API Version**: v1.0.0
**Documentation Version**: 1.0.0

For the most up-to-date information, please refer to our [live documentation](https://docs.ai-ppt-assistant.com).