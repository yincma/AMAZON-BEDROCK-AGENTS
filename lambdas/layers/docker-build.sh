#!/bin/bash

# Docker-based Lambda Layer Build Script for AI PPT Assistant
# Ensures Python 3.12 Lambda runtime compatibility

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
readonly PYTHON_VERSION="3.12"
readonly LAYER_NAME="ai-ppt-assistant-dependencies"
readonly BUILD_DIR="build"
readonly OUTPUT_DIR="dist"
readonly ARCHITECTURE="arm64"
readonly DOCKER_IMAGE_NAME="${LAYER_NAME}-builder"
readonly LAMBDA_BASE_IMAGE="public.ecr.aws/lambda/python:${PYTHON_VERSION}-${ARCHITECTURE}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Docker Lambda Layer Build Script${NC}"
echo -e "${GREEN}Python Version: ${PYTHON_VERSION}${NC}"
echo -e "${GREEN}Architecture: ${ARCHITECTURE}${NC}"
echo -e "${GREEN}Base Image: ${LAMBDA_BASE_IMAGE}${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check Docker availability
check_docker() {
    echo -e "${BLUE}Checking Docker availability...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker not found${NC}"
        echo -e "${YELLOW}Please install Docker to use this build script${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon not running${NC}"
        echo -e "${YELLOW}Please start Docker daemon${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Docker is available and running${NC}"
}

# Function to validate requirements.txt
validate_requirements() {
    echo -e "${BLUE}Validating requirements.txt...${NC}"
    
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}Error: requirements.txt not found${NC}"
        exit 1
    fi
    
    # Check for aws-lambda-powertools version
    if grep -q "aws-lambda-powertools==2.39.0" requirements.txt; then
        echo -e "${YELLOW}Warning: aws-lambda-powertools 2.39.0 has known issues${NC}"
        echo -e "${YELLOW}Consider using 2.38.0 for stability${NC}"
    fi
    
    echo -e "${GREEN}Requirements validation completed${NC}"
}

# Function to clean previous builds
clean_build() {
    echo -e "${YELLOW}Cleaning previous builds...${NC}"
    
    rm -rf "$BUILD_DIR" "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
    
    # Remove old Docker image if exists
    if docker images -q "$DOCKER_IMAGE_NAME" &> /dev/null; then
        echo -e "${YELLOW}Removing previous Docker image...${NC}"
        docker rmi "$DOCKER_IMAGE_NAME" &> /dev/null || true
    fi
    
    echo -e "${GREEN}Cleanup completed${NC}"
}

# Function to create optimized Dockerfile
create_dockerfile() {
    echo -e "${BLUE}Creating optimized Dockerfile...${NC}"
    
    cat > Dockerfile.layer <<EOF
# Use official AWS Lambda Python base image for ARM64
FROM --platform=linux/${ARCHITECTURE} ${LAMBDA_BASE_IMAGE}

# Set working directory
WORKDIR /var/task

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install system dependencies if needed
RUN yum update -y && \\
    yum clean all && \\
    rm -rf /var/cache/yum

# Create python directory structure matching Lambda layer expectations
RUN mkdir -p /opt/python/lib/python${PYTHON_VERSION}/site-packages

# Install Python packages with precise targeting for Lambda runtime
RUN pip install --no-cache-dir \\
    --target /opt/python/lib/python${PYTHON_VERSION}/site-packages \\
    --platform linux_aarch64 \\
    --implementation cp \\
    --python-version ${PYTHON_VERSION} \\
    --only-binary=:all: \\
    --upgrade \\
    -r /tmp/requirements.txt

# Optimize layer size by removing unnecessary files
RUN find /opt/python -type f -name "*.pyc" -delete && \\
    find /opt/python -type f -name "*.pyo" -delete && \\
    find /opt/python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \\
    find /opt/python -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true && \\
    find /opt/python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true && \\
    find /opt/python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \\
    find /opt/python -name "*.so" -exec strip {} + 2>/dev/null || true

# Remove documentation and examples to reduce size
RUN find /opt/python -type d -name "doc" -exec rm -rf {} + 2>/dev/null || true && \\
    find /opt/python -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \\
    find /opt/python -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true && \\
    find /opt/python -name "*.txt" -path "*/site-packages/*" -delete 2>/dev/null || true

# Set permissions
RUN chmod -R 755 /opt/python

# Verify Python installation
RUN ls -la /opt/python/lib/python${PYTHON_VERSION}/site-packages/ | head -10
EOF
    
    echo -e "${GREEN}Dockerfile created successfully${NC}"
}

# Function to build Docker image and extract layer
build_layer() {
    echo -e "${BLUE}Building Docker image...${NC}"
    
    # Build the Docker image with build arguments
    docker build \\
        --platform=linux/${ARCHITECTURE} \\
        --file Dockerfile.layer \\
        --tag "$DOCKER_IMAGE_NAME" \\
        --progress=plain \\
        .
    
    echo -e "${BLUE}Extracting layer from Docker container...${NC}"
    
    # Create a container and copy the layer
    CONTAINER_ID=$(docker create --platform=linux/${ARCHITECTURE} "$DOCKER_IMAGE_NAME")
    
    # Copy python directory and create zip
    docker cp "$CONTAINER_ID":/opt/python ./python
    
    # Create zip file with proper structure
    echo -e "${BLUE}Creating layer package...${NC}"
    zip -r -q "$OUTPUT_DIR/${LAYER_NAME}.zip" python/
    
    # Cleanup
    rm -rf python/
    docker rm "$CONTAINER_ID" &> /dev/null
    
    echo -e "${GREEN}Layer package created: $OUTPUT_DIR/${LAYER_NAME}.zip${NC}"
}

# Function to verify the layer package
verify_layer() {
    echo -e "${BLUE}Verifying layer package...${NC}"
    
    if [ ! -f "$OUTPUT_DIR/${LAYER_NAME}.zip" ]; then
        echo -e "${RED}Error: Layer package not found${NC}"
        exit 1
    fi
    
    # Check file size
    SIZE=$(du -h "$OUTPUT_DIR/${LAYER_NAME}.zip" | cut -f1)
    SIZE_BYTES=$(stat -f%z "$OUTPUT_DIR/${LAYER_NAME}.zip" 2>/dev/null || stat -c%s "$OUTPUT_DIR/${LAYER_NAME}.zip")
    
    echo -e "${GREEN}Layer size: $SIZE (${SIZE_BYTES} bytes)${NC}"
    
    # Check Lambda limits
    MAX_LAYER_SIZE=$((250 * 1024 * 1024))  # 250MB unzipped
    MAX_ZIPPED_SIZE=$((50 * 1024 * 1024))   # ~50MB zipped (rough estimate)
    
    if [ $SIZE_BYTES -gt $MAX_ZIPPED_SIZE ]; then
        echo -e "${YELLOW}Warning: Layer size might exceed Lambda limits when unzipped${NC}"
        echo -e "${YELLOW}Consider optimizing dependencies${NC}"
    fi
    
    # Verify package structure
    echo -e "${BLUE}Verifying package structure...${NC}"
    if unzip -t "$OUTPUT_DIR/${LAYER_NAME}.zip" &> /dev/null; then
        echo -e "${GREEN}Package integrity verified${NC}"
    else
        echo -e "${RED}Error: Package is corrupted${NC}"
        exit 1
    fi
    
    # Show top-level contents
    echo -e "${BLUE}Package contents (top 20 entries):${NC}"
    unzip -l "$OUTPUT_DIR/${LAYER_NAME}.zip" | head -25
}

# Function to generate layer metadata
generate_metadata() {
    echo -e "${BLUE}Generating layer metadata...${NC}"
    
    local BUILD_DATE
    BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    local SIZE_BYTES
    SIZE_BYTES=$(stat -f%z "$OUTPUT_DIR/${LAYER_NAME}.zip" 2>/dev/null || stat -c%s "$OUTPUT_DIR/${LAYER_NAME}.zip")
    
    cat > "$OUTPUT_DIR/layer-metadata.json" <<EOF
{
    "name": "${LAYER_NAME}",
    "description": "Shared dependencies for AI PPT Assistant Lambda functions (Docker built)",
    "compatible_runtimes": ["python${PYTHON_VERSION}"],
    "compatible_architectures": ["${ARCHITECTURE}"],
    "license": "MIT",
    "build_info": {
        "build_date": "${BUILD_DATE}",
        "build_method": "docker",
        "base_image": "${LAMBDA_BASE_IMAGE}",
        "python_version": "${PYTHON_VERSION}",
        "architecture": "${ARCHITECTURE}",
        "size_bytes": ${SIZE_BYTES}
    },
    "deployment": {
        "aws_cli_command": "aws lambda publish-layer-version --layer-name ${LAYER_NAME} --description 'Docker-built dependencies for AI PPT Assistant' --zip-file fileb://$OUTPUT_DIR/${LAYER_NAME}.zip --compatible-runtimes python${PYTHON_VERSION} --compatible-architectures ${ARCHITECTURE}"
    }
}
EOF
    
    echo -e "${GREEN}Layer metadata created: $OUTPUT_DIR/layer-metadata.json${NC}"
}

# Function to cleanup Docker resources
cleanup_docker() {
    echo -e "${YELLOW}Cleaning up Docker resources...${NC}"
    
    # Remove Dockerfile
    rm -f Dockerfile.layer
    
    # Remove Docker image
    if docker images -q "$DOCKER_IMAGE_NAME" &> /dev/null; then
        docker rmi "$DOCKER_IMAGE_NAME" &> /dev/null || true
    fi
    
    echo -e "${GREEN}Docker cleanup completed${NC}"
}

# Function to display deployment instructions
show_deployment_instructions() {
    echo -e "\\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    echo -e "\\n${BLUE}Deployment Instructions:${NC}"
    echo -e "${YELLOW}1. Upload layer to AWS Lambda:${NC}"
    echo -e "aws lambda publish-layer-version \\\\"
    echo -e "  --layer-name ${LAYER_NAME} \\\\"
    echo -e "  --description 'Docker-built dependencies for AI PPT Assistant' \\\\"
    echo -e "  --zip-file fileb://$OUTPUT_DIR/${LAYER_NAME}.zip \\\\"
    echo -e "  --compatible-runtimes python${PYTHON_VERSION} \\\\"
    echo -e "  --compatible-architectures ${ARCHITECTURE}"
    
    echo -e "\\n${YELLOW}2. Update Terraform configuration:${NC}"
    echo -e "Update the layer version in your Lambda function configurations"
    
    echo -e "\\n${YELLOW}3. Test deployment:${NC}"
    echo -e "Deploy and test a Lambda function using this layer"
}

# Main execution function
main() {
    local KEEP_DOCKER=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --keep-docker)
                KEEP_DOCKER=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--keep-docker] [--help]"
                echo ""
                echo "Options:"
                echo "  --keep-docker    Keep Docker image after build"
                echo "  --help, -h       Show this help message"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done
    
    # Execute build pipeline
    check_docker
    validate_requirements
    clean_build
    create_dockerfile
    build_layer
    verify_layer
    generate_metadata
    
    if [ "$KEEP_DOCKER" = false ]; then
        cleanup_docker
    else
        echo -e "${YELLOW}Docker image preserved: $DOCKER_IMAGE_NAME${NC}"
    fi
    
    show_deployment_instructions
}

# Error handling
trap 'echo -e "${RED}Build failed! Check the error above.${NC}"; cleanup_docker; exit 1' ERR

# Run main function
main "$@"