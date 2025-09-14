#!/bin/bash

# AI PPT Assistant - Infrastructure Deployment Script
# Phase 3: Performance Optimization with Step Functions

set -e

echo "========================================="
echo "AI PPT Assistant - Infrastructure Deploy"
echo "Phase 3: Performance Optimization"
echo "========================================="

# Check AWS credentials
echo "Checking AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1 || {
    echo "Error: AWS credentials not configured"
    echo "Please run: aws configure"
    exit 1
}

# Create lambda-packages directory if it doesn't exist
mkdir -p ../lambda-packages

# Package Lambda functions
echo "Packaging Lambda functions..."

# Package workflow orchestrator
if [ -f "../lambdas/workflow_orchestrator.py" ]; then
    echo "  - Packaging workflow_orchestrator..."
    cd ../lambdas
    zip -q ../lambda-packages/workflow_orchestrator.zip workflow_orchestrator.py
    cd ../infrastructure
fi

# Package content generator (if exists)
if [ -f "../lambdas/content_generator.py" ]; then
    echo "  - Packaging content_generator..."
    cd ../lambdas
    zip -q ../lambda-packages/content_generator.zip content_generator.py
    cd ../infrastructure
fi

# Package image generator (if exists)
if [ -f "../lambdas/image_generator.py" ]; then
    echo "  - Packaging image_generator..."
    cd ../lambdas
    zip -q ../lambda-packages/image_generator.zip image_generator.py image_*.py
    cd ../infrastructure
fi

# Package compile PPT (if exists)
if [ -f "../lambdas/compile_ppt.py" ]; then
    echo "  - Packaging compile_ppt..."
    cd ../lambdas
    zip -q ../lambda-packages/compile_ppt.zip compile_ppt.py ppt_styler.py
    cd ../infrastructure
fi

# Use placeholder for missing functions
echo "  - Creating placeholder packages for missing functions..."
for func in api_handler generate_ppt_complete status_check download_ppt content_generator image_generator compile_ppt workflow_orchestrator; do
    if [ ! -f "../lambda-packages/${func}.zip" ]; then
        echo "    Creating placeholder for ${func}..."
        echo "def handler(event, context): return {'statusCode': 200, 'body': 'Placeholder'}" > /tmp/${func}_placeholder.py
        zip -jq ../lambda-packages/${func}.zip /tmp/${func}_placeholder.py
        rm /tmp/${func}_placeholder.py
    fi
done

# Create dependencies layer if it doesn't exist
if [ ! -f "../ai-ppt-dependencies-layer.zip" ]; then
    echo "Creating dependencies layer placeholder..."
    mkdir -p /tmp/python
    echo "# Placeholder for dependencies" > /tmp/python/placeholder.py
    cd /tmp
    zip -rq ai-ppt-dependencies-layer.zip python/
    mv ai-ppt-dependencies-layer.zip ../
    cd -
    rm -rf /tmp/python
fi

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

# Validate configuration
echo "Validating Terraform configuration..."
terraform validate

# Show plan
echo "Creating deployment plan..."
terraform plan -out=tfplan

# Ask for confirmation
echo ""
echo "========================================="
echo "Ready to deploy infrastructure?"
read -p "Type 'yes' to continue: " confirm

if [ "$confirm" = "yes" ]; then
    echo "Deploying infrastructure..."
    terraform apply tfplan

    echo ""
    echo "========================================="
    echo "Deployment complete!"
    echo "========================================="
    echo ""
    terraform output
else
    echo "Deployment cancelled."
    rm -f tfplan
fi