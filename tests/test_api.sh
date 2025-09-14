#!/bin/bash

# AI PPT Assistant - API Test Script

set -e

echo "========================================="
echo "AI PPT Assistant - API Test"
echo "========================================="

# Get API Gateway URL from Terraform output
cd infrastructure
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
cd ..

if [ -z "$API_URL" ]; then
    echo "Error: Could not get API URL. Make sure infrastructure is deployed."
    exit 1
fi

echo "API URL: $API_URL"
echo ""

# Test 1: Generate PPT
echo "Test 1: Generating PPT..."
RESPONSE=$(curl -s -X POST $API_URL/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Introduction to AI"}')

echo "Response: $RESPONSE"
PRESENTATION_ID=$(echo $RESPONSE | grep -o '"presentation_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$PRESENTATION_ID" ]; then
    echo "Error: Could not extract presentation_id"
    exit 1
fi

echo "Presentation ID: $PRESENTATION_ID"
echo ""

# Test 2: Check status
echo "Test 2: Checking status..."
sleep 2
STATUS_RESPONSE=$(curl -s -X GET $API_URL/status/$PRESENTATION_ID)
echo "Status Response: $STATUS_RESPONSE"
echo ""

# Test 3: Get download URL
echo "Test 3: Getting download URL..."
DOWNLOAD_RESPONSE=$(curl -s -X GET $API_URL/download/$PRESENTATION_ID)
echo "Download Response: $DOWNLOAD_RESPONSE"
echo ""

echo "========================================="
echo "API tests completed!"
echo "========================================="