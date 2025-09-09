#!/bin/bash

# Remaining CloudFront distributions
DISTRIBUTIONS=("EPUE8A24BHITU" "E3I0T1Y6KQSTE")

echo "Monitoring and deleting remaining CloudFront distributions..."

for DIST_ID in "${DISTRIBUTIONS[@]}"; do
    echo "Processing distribution: $DIST_ID"
    
    # Wait for distribution to be deployed if it's in progress
    STATUS=$(aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.Status" --output text 2>/dev/null)
    
    if [ -z "$STATUS" ]; then
        echo "  - Distribution $DIST_ID not found or already deleted"
        continue
    fi
    
    if [ "$STATUS" == "InProgress" ]; then
        echo "  - Waiting for distribution to complete deployment (this may take 15-30 minutes)..."
        
        # Check status every 30 seconds for up to 30 minutes
        COUNTER=0
        MAX_ATTEMPTS=60
        
        while [ "$STATUS" == "InProgress" ] && [ $COUNTER -lt $MAX_ATTEMPTS ]; do
            sleep 30
            STATUS=$(aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.Status" --output text 2>/dev/null)
            COUNTER=$((COUNTER + 1))
            
            if [ $((COUNTER % 4)) -eq 0 ]; then
                echo "    Still waiting... ($(($COUNTER / 2)) minutes elapsed)"
            fi
        done
    fi
    
    if [ "$STATUS" == "Deployed" ]; then
        # Get the current ETag
        aws cloudfront get-distribution-config --id "$DIST_ID" > /tmp/dist-config-$DIST_ID-final.json 2>&1
        ETAG=$(jq -r '.ETag' /tmp/dist-config-$DIST_ID-final.json)
        
        # Check if distribution is disabled
        ENABLED=$(jq -r '.DistributionConfig.Enabled' /tmp/dist-config-$DIST_ID-final.json)
        
        if [ "$ENABLED" == "false" ]; then
            echo "  - Deleting distribution..."
            aws cloudfront delete-distribution --id "$DIST_ID" --if-match "$ETAG" 2>&1
            
            if [ $? -eq 0 ]; then
                echo "  - Distribution $DIST_ID deleted successfully"
            else
                echo "  - Failed to delete distribution $DIST_ID"
            fi
        else
            echo "  - Distribution $DIST_ID is still enabled, cannot delete"
        fi
    else
        echo "  - Distribution $DIST_ID status: $STATUS"
    fi
    
    echo ""
done

echo "CloudFront distribution cleanup completed"