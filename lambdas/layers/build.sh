#!/bin/bash

# Lambda Layer Build Script for AI PPT Assistant
# Builds Lambda layer packages for Python 3.13 runtime

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.13"
LAYER_NAME="ai-ppt-assistant-dependencies"
BUILD_DIR="build"
PACKAGE_DIR="python"
OUTPUT_DIR="dist"
ARCHITECTURE="arm64"  # Graviton2 for cost optimization

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Lambda Layer Build Script${NC}"
echo -e "${GREEN}Python Version: ${PYTHON_VERSION}${NC}"
echo -e "${GREEN}Architecture: ${ARCHITECTURE}${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check Python version
check_python_version() {
    if command -v python3.13 &> /dev/null; then
        PYTHON_CMD="python3.13"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        # Check if it's actually 3.13
        ACTUAL_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        if [[ "$ACTUAL_VERSION" != "3.13" ]]; then
            echo -e "${YELLOW}Warning: Python version is $ACTUAL_VERSION, not 3.13${NC}"
            echo -e "${YELLOW}Consider using Docker for accurate builds${NC}"
        fi
    else
        echo -e "${RED}Error: Python 3 not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}Using Python command: $PYTHON_CMD${NC}"
}

# Function to clean previous builds
clean_build() {
    echo -e "${YELLOW}Cleaning previous builds...${NC}"
    rm -rf "$BUILD_DIR" "$OUTPUT_DIR"
    mkdir -p "$BUILD_DIR/$PACKAGE_DIR/lib/python${PYTHON_VERSION}/site-packages"
    mkdir -p "$OUTPUT_DIR"
}

# Function to build layer locally
build_local() {
    echo -e "${GREEN}Building layer locally...${NC}"
    
    # Install packages to the correct directory structure
    $PYTHON_CMD -m pip install \
        -r requirements.txt \
        -t "$BUILD_DIR/$PACKAGE_DIR/lib/python${PYTHON_VERSION}/site-packages" \
        --upgrade \
        --no-cache-dir
    
    # Create the zip file
    cd "$BUILD_DIR"
    zip -r -q "../$OUTPUT_DIR/${LAYER_NAME}.zip" .
    cd ..
    
    echo -e "${GREEN}Layer package created: $OUTPUT_DIR/${LAYER_NAME}.zip${NC}"
}

# Function to build layer using Docker (recommended for production)
build_docker() {
    echo -e "${GREEN}Building layer using Docker...${NC}"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker not found${NC}"
        echo -e "${YELLOW}Install Docker or use --local flag${NC}"
        exit 1
    fi
    
    # Create a temporary Dockerfile for ARM64
    cat > Dockerfile.layer <<EOF
FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.13-arm64

# Copy requirements file
COPY requirements.txt /tmp/

# Install packages for ARM64 architecture
RUN pip install -r /tmp/requirements.txt -t /opt/python/lib/python3.13/site-packages/ \\
    --platform linux_aarch64 \\
    --implementation cp \\
    --python-version 3.13 \\
    --only-binary=:all: \\
    --upgrade \\
    --no-cache-dir

# Clean up to reduce size
RUN find /opt/python -type f -name "*.pyc" -delete
RUN find /opt/python -type d -name "__pycache__" -delete
RUN find /opt/python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
RUN find /opt/python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
RUN find /opt/python -name "*.so" -exec strip {} + 2>/dev/null || true
EOF

    # Build Docker image for ARM64
    docker build --platform=linux/arm64 -f Dockerfile.layer -t ${LAYER_NAME}-builder .
    
    # Extract the layer
    docker run --rm -v "$PWD/$OUTPUT_DIR":/output ${LAYER_NAME}-builder \
        bash -c "cd /opt && zip -r -q /output/${LAYER_NAME}.zip python/"
    
    # Clean up
    rm -f Dockerfile.layer
    docker rmi ${LAYER_NAME}-builder
    
    echo -e "${GREEN}Layer package created: $OUTPUT_DIR/${LAYER_NAME}.zip${NC}"
}

# Function to verify the layer
verify_layer() {
    echo -e "${YELLOW}Verifying layer package...${NC}"
    
    if [ -f "$OUTPUT_DIR/${LAYER_NAME}.zip" ]; then
        SIZE=$(du -h "$OUTPUT_DIR/${LAYER_NAME}.zip" | cut -f1)
        echo -e "${GREEN}Layer size: $SIZE${NC}"
        
        # Check if size is under Lambda limit (250MB unzipped)
        SIZE_BYTES=$(stat -f%z "$OUTPUT_DIR/${LAYER_NAME}.zip" 2>/dev/null || stat -c%s "$OUTPUT_DIR/${LAYER_NAME}.zip")
        if [ $SIZE_BYTES -gt 52428800 ]; then  # 50MB zipped (approximate)
            echo -e "${YELLOW}Warning: Layer size might exceed Lambda limits when unzipped${NC}"
        fi
        
        # List contents
        echo -e "${GREEN}Layer contents:${NC}"
        unzip -l "$OUTPUT_DIR/${LAYER_NAME}.zip" | head -20
        echo "..."
    else
        echo -e "${RED}Error: Layer package not found${NC}"
        exit 1
    fi
}

# Function to create layer version info
create_layer_info() {
    echo -e "${YELLOW}Creating layer version info...${NC}"
    
    cat > "$OUTPUT_DIR/layer-info.json" <<EOF
{
    "name": "${LAYER_NAME}",
    "description": "Shared dependencies for AI PPT Assistant Lambda functions",
    "compatible_runtimes": ["python3.13"],
    "compatible_architectures": ["${ARCHITECTURE}"],
    "license": "MIT",
    "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "dependencies": {
        "boto3": "1.35.0",
        "python-pptx": "0.6.23",
        "Pillow": "10.4.0",
        "aws-lambda-powertools": "2.39.0"
    }
}
EOF
    
    echo -e "${GREEN}Layer info created: $OUTPUT_DIR/layer-info.json${NC}"
}

# Main execution
main() {
    # Parse arguments
    # Default to local build due to Docker issues with Lambda base image
    BUILD_METHOD="local"
    if [[ "$1" == "--docker" ]]; then
        BUILD_METHOD="docker"
    fi
    
    # Check Python version
    if [[ "$BUILD_METHOD" == "local" ]]; then
        check_python_version
    fi
    
    # Clean and prepare
    clean_build
    
    # Build the layer
    if [[ "$BUILD_METHOD" == "docker" ]]; then
        build_docker
    else
        build_local
    fi
    
    # Verify and document
    verify_layer
    create_layer_info
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}Layer package: $OUTPUT_DIR/${LAYER_NAME}.zip${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Provide upload instructions
    echo -e "\n${YELLOW}To deploy this layer to AWS:${NC}"
    echo -e "aws lambda publish-layer-version \\"
    echo -e "  --layer-name ${LAYER_NAME} \\"
    echo -e "  --description 'Shared dependencies for AI PPT Assistant' \\"
    echo -e "  --zip-file fileb://$OUTPUT_DIR/${LAYER_NAME}.zip \\"
    echo -e "  --compatible-runtimes python3.13 \\"
    echo -e "  --compatible-architectures ${ARCHITECTURE}"
}

# Run main function
main "$@"