#!/bin/bash

# CloudFront Resources Pre-Check Script
# This script checks CloudFront resources status before deployment or destruction
# Version: 1.0
# Author: ultrathink

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_NAME="ai-ppt-assistant"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}CloudFront Resources Status Check${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to print info
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check 1: CloudFront Origin Access Identities
print_status "Checking CloudFront Origin Access Identities..."

OAI_COUNT=$(aws cloudfront list-cloud-front-origin-access-identities --query "CloudFrontOriginAccessIdentityList.Items | length(@)" --output text 2>/dev/null || echo "0")

if [ "$OAI_COUNT" -eq 0 ]; then
    print_success "No CloudFront OAIs found"
else
    print_warning "Found $OAI_COUNT CloudFront OAI(s):"
    
    # List all OAIs with details
    aws cloudfront list-cloud-front-origin-access-identities \
        --query "CloudFrontOriginAccessIdentityList.Items[].{ID:Id,Comment:Comment}" \
        --output table 2>/dev/null || echo "Error listing OAIs"
    
    # For each OAI, check if it's being used
    OAI_IDS=$(aws cloudfront list-cloud-front-origin-access-identities --query "CloudFrontOriginAccessIdentityList.Items[].Id" --output text 2>/dev/null || echo "")
    
    for OAI_ID in $OAI_IDS; do
        echo ""
        print_info "Checking usage for OAI: $OAI_ID"
        
        # Find distributions using this OAI
        DISTRIBUTIONS=$(aws cloudfront list-distributions \
            --query "DistributionList.Items[?Origins.Items[?S3OriginConfig.OriginAccessIdentity=='origin-access-identity/cloudfront/${OAI_ID}']].{ID:Id,DomainName:DomainName,Status:Status,Enabled:Enabled}" \
            --output json 2>/dev/null || echo "[]")
        
        if [ "$DISTRIBUTIONS" == "[]" ] || [ "$DISTRIBUTIONS" == "null" ] || [ -z "$DISTRIBUTIONS" ]; then
            print_success "  OAI $OAI_ID is not being used by any distributions"
        else
            DIST_COUNT=$(echo "$DISTRIBUTIONS" | jq '. | if type == "array" then length else 0 end')
            if [ "$DIST_COUNT" -eq 0 ]; then
                print_success "  OAI $OAI_ID is not being used by any distributions"
            else
                print_warning "  OAI $OAI_ID is being used by $DIST_COUNT distribution(s):"
                echo "$DISTRIBUTIONS" | jq -r '.[] | "    - \(.ID) (\(.DomainName)) - Status: \(.Status), Enabled: \(.Enabled)"'
            fi
        fi
    done
fi

echo ""

# Check 2: CloudFront Distributions
print_status "Checking CloudFront Distributions..."

DIST_COUNT=$(aws cloudfront list-distributions --query "DistributionList.Items | length(@)" --output text 2>/dev/null || echo "0")

if [ "$DIST_COUNT" -eq 0 ]; then
    print_success "No CloudFront distributions found"
else
    print_warning "Found $DIST_COUNT CloudFront distribution(s):"
    
    # List all distributions with details
    aws cloudfront list-distributions \
        --query "DistributionList.Items[].{ID:Id,DomainName:DomainName,Status:Status,Enabled:Enabled}" \
        --output table 2>/dev/null || echo "Error listing distributions"
    
    # Count distributions by status
    ENABLED_COUNT=$(aws cloudfront list-distributions --query "DistributionList.Items[?Enabled==\`true\`] | length(@)" --output text 2>/dev/null || echo "0")
    DISABLED_COUNT=$(aws cloudfront list-distributions --query "DistributionList.Items[?Enabled==\`false\`] | length(@)" --output text 2>/dev/null || echo "0")
    INPROGRESS_COUNT=$(aws cloudfront list-distributions --query "DistributionList.Items[?Status=='InProgress'] | length(@)" --output text 2>/dev/null || echo "0")
    
    echo ""
    print_info "Distribution Summary:"
    echo "  - Enabled: $ENABLED_COUNT"
    echo "  - Disabled: $DISABLED_COUNT"
    echo "  - In Progress: $INPROGRESS_COUNT"
fi

echo ""

# Check 3: Estimate Cleanup Time
print_status "Estimating cleanup time if destruction is needed..."

TOTAL_TIME=0

if [ "$OAI_COUNT" -gt 0 ]; then
    # Check if any OAIs are in use
    USED_OAIS=0
    for OAI_ID in $OAI_IDS; do
        DIST_FOR_OAI=$(aws cloudfront list-distributions \
            --query "DistributionList.Items[?Origins.Items[?S3OriginConfig.OriginAccessIdentity=='origin-access-identity/cloudfront/${OAI_ID}']] | length(@)" \
            --output text 2>/dev/null || echo "0")
        if [ "$DIST_FOR_OAI" -gt 0 ]; then
            USED_OAIS=$((USED_OAIS + 1))
        fi
    done
    
    if [ "$USED_OAIS" -gt 0 ]; then
        # Estimate 15-30 minutes for CloudFront distribution cleanup
        TOTAL_TIME=$((TOTAL_TIME + 20))
        print_warning "CloudFront distributions need to be disabled and deleted (estimated 15-30 minutes)"
    fi
fi

# Add time for Terraform destroy
TOTAL_TIME=$((TOTAL_TIME + 5))

print_info "Estimated total cleanup time: ${TOTAL_TIME} minutes"

echo ""

# Check 4: Provide Recommendations
print_status "Recommendations:"

if [ "$DIST_COUNT" -gt 0 ] || [ "$OAI_COUNT" -gt 0 ]; then
    print_warning "CloudFront resources detected. Use 'make destroy' for safe cleanup."
    print_info "The enhanced destroy script will automatically:"
    echo "  1. Disable all CloudFront distributions"
    echo "  2. Wait for global propagation"
    echo "  3. Delete distributions"
    echo "  4. Delete OAIs"
    echo "  5. Run Terraform destroy"
else
    print_success "No CloudFront resources found. Safe to proceed with standard destroy."
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Check Complete${NC}"
echo -e "${CYAN}========================================${NC}"