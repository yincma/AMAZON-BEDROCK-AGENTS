# Lambda Layers - AI PPT Assistant

## Overview

This directory contains the Lambda Layer configuration for the AI PPT Assistant project. The layer includes all shared dependencies required by the Lambda functions, optimized for Python 3.13 runtime.

## Structure

```
lambdas/layers/
├── requirements.txt    # Python dependencies
├── build.sh           # Build script for creating layer package
├── README.md          # This file
└── dist/              # Output directory (created during build)
    └── ai-ppt-assistant-dependencies.zip
```

## Dependencies

Key dependencies included in the layer:

- **AWS SDK**: `boto3`, `botocore` - For AWS service interactions
- **PowerPoint**: `python-pptx` - For PPTX file generation
- **Image Processing**: `Pillow` - For image manipulation
- **Async Support**: `aioboto3`, `aiohttp` - For Python 3.13 async operations
- **Monitoring**: `aws-lambda-powertools`, `aws-xray-sdk` - For observability
- **Data Validation**: `pydantic`, `jsonschema` - For input validation

## Building the Layer

### Prerequisites

- Python 3.13 (recommended) or Docker
- AWS CLI configured
- Sufficient disk space (~500MB)

### Build Methods

#### Method 1: Docker Build (Recommended for Production)

```bash
./build.sh
```

This uses the official AWS Lambda Python 3.13 base image to ensure compatibility.

#### Method 2: Local Build

```bash
./build.sh --local
```

Uses your local Python installation. May have compatibility issues if not using Python 3.13.

### Build Output

The script creates:
- `dist/ai-ppt-assistant-dependencies.zip` - The layer package
- `dist/layer-info.json` - Metadata about the layer

## Deploying the Layer

### Using AWS CLI

```bash
aws lambda publish-layer-version \
  --layer-name ai-ppt-assistant-dependencies \
  --description "Shared dependencies for AI PPT Assistant" \
  --zip-file fileb://dist/ai-ppt-assistant-dependencies.zip \
  --compatible-runtimes python3.13 \
  --compatible-architectures x86_64
```

### Using Terraform

The layer is automatically deployed via the Terraform configuration in `infrastructure/modules/lambda/`.

## Using the Layer in Lambda Functions

### Python Code

```python
# Dependencies from the layer are automatically available
import boto3
from pptx import Presentation
from PIL import Image
from aws_lambda_powertools import Logger

logger = Logger()

def lambda_handler(event, context):
    # Your function code here
    pass
```

### Function Configuration

Add the layer ARN to your Lambda function:

```python
# In Terraform
layers = [aws_lambda_layer_version.dependencies.arn]

# Or via AWS CLI
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:region:account:layer:ai-ppt-assistant-dependencies:1
```

## Layer Size Optimization

The layer is optimized for size by:
- Using `--only-binary=:all:` flag for binary packages
- Removing `*.pyc` files and `__pycache__` directories
- Excluding test directories and documentation
- Using specific package versions to avoid dependency bloat

## Updating Dependencies

1. Edit `requirements.txt` to add/update packages
2. Rebuild the layer: `./build.sh`
3. Test with a sample Lambda function
4. Deploy the new layer version
5. Update Lambda functions to use the new layer version

## Troubleshooting

### Common Issues

1. **Layer too large**: 
   - Remove unnecessary dependencies
   - Consider splitting into multiple layers
   - Use Lambda container images for large dependencies

2. **Import errors**:
   - Ensure Python version compatibility
   - Rebuild using Docker method
   - Check package architecture (x86_64 vs arm64)

3. **Build failures**:
   - Clear Docker cache: `docker system prune`
   - Update pip: `pip install --upgrade pip`
   - Check disk space availability

## Best Practices

1. **Version Management**: Always version your layers and reference specific versions in Lambda functions
2. **Testing**: Test new layer versions in a dev environment before production
3. **Documentation**: Keep layer-info.json updated with current dependencies
4. **Security**: Regularly update dependencies for security patches
5. **Size Monitoring**: Monitor layer size to stay within Lambda limits (250MB unzipped)

## Layer Limits

- **Max size (zipped)**: 50 MB for direct upload, 250 MB via S3
- **Max size (unzipped)**: 250 MB
- **Max layers per function**: 5
- **Total unzipped size**: 250 MB (including function code)

## Support

For issues or questions about the Lambda layers, please refer to the main project documentation or create an issue in the project repository.