#!/bin/bash
set -euo pipefail

# Build minimal layer using Docker for Lambda ARM64 Python 3.12
echo "Building minimal layer with Docker for Lambda ARM64..."

# Create temporary directory for build
mkdir -p build/minimal-docker
cd build/minimal-docker

# Copy requirements file
cp ../../requirements-minimal.txt requirements.txt

# Create Dockerfile for building
cat > Dockerfile <<'EOF'
FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.12-arm64

WORKDIR /var/task

COPY requirements.txt /tmp/requirements.txt

# Use dnf (not yum) for Amazon Linux 2023
RUN dnf update -y && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Create python directory structure
RUN mkdir -p /opt/python

# Install Python packages for ARM64 Lambda runtime
RUN pip install --no-cache-dir \
    --target /opt/python \
    --platform manylinux2014_aarch64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    -r /tmp/requirements.txt

# Remove unnecessary files
RUN find /opt/python -type f -name "*.pyc" -delete && \
    find /opt/python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

RUN chmod -R 755 /opt/python
EOF

# Build the Docker image
docker build --platform linux/arm64 -t minimal-layer-builder .

# Create container and copy the layer files
docker create --name minimal-layer-extract minimal-layer-builder
docker cp minimal-layer-extract:/opt/python .
docker rm minimal-layer-extract

# Create the layer zip
zip -r ../../dist/ai-ppt-assistant-minimal.zip python/

# Clean up
cd ../..
rm -rf build/minimal-docker

echo "Minimal layer built successfully!"
echo "Layer file: dist/ai-ppt-assistant-minimal.zip"
ls -lh dist/ai-ppt-assistant-minimal.zip