#!/bin/bash

# CloudFront distributions using the OAI
DISTRIBUTIONS=("E1Z37RRJ6KVIND" "E1XS22VUXKVJUV" "EPUE8A24BHITU" "E3I0T1Y6KQSTE")

echo "Starting to disable and delete CloudFront distributions..."

for DIST_ID in "${DISTRIBUTIONS[@]}"; do
    echo "Processing distribution: $DIST_ID"
    
    # Get the distribution config
    echo "  - Getting distribution config..."
    aws cloudfront get-distribution-config --id "$DIST_ID" > /tmp/dist-config-$DIST_ID.json 2>&1
    
    if [ $? -eq 0 ]; then
        # Extract ETag
        ETAG=$(jq -r '.ETag' /tmp/dist-config-$DIST_ID.json)
        
        # Extract and modify the distribution config to disable it
        jq '.DistributionConfig.Enabled = false' /tmp/dist-config-$DIST_ID.json | jq '.DistributionConfig' > /tmp/dist-config-update-$DIST_ID.json
        
        # Update the distribution to disable it
        echo "  - Disabling distribution..."
        aws cloudfront update-distribution \
            --id "$DIST_ID" \
            --distribution-config file:///tmp/dist-config-update-$DIST_ID.json \
            --if-match "$ETAG" > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo "  - Distribution disabled successfully"
            
            # Wait for the distribution to be deployed
            echo "  - Waiting for distribution to be deployed (this may take several minutes)..."
            aws cloudfront wait distribution-deployed --id "$DIST_ID" 2>&1
            
            # Get the new ETag after the update
            aws cloudfront get-distribution-config --id "$DIST_ID" > /tmp/dist-config-$DIST_ID-disabled.json 2>&1
            ETAG_DISABLED=$(jq -r '.ETag' /tmp/dist-config-$DIST_ID-disabled.json)
            
            # Delete the distribution
            echo "  - Deleting distribution..."
            aws cloudfront delete-distribution --id "$DIST_ID" --if-match "$ETAG_DISABLED" 2>&1
            
            if [ $? -eq 0 ]; then
                echo "  - Distribution $DIST_ID deleted successfully"
            else
                echo "  - Failed to delete distribution $DIST_ID"
            fi
        else
            echo "  - Failed to disable distribution $DIST_ID"
        fi
    else
        echo "  - Distribution $DIST_ID not found or already deleted"
    fi
    
    echo ""
done

echo "CloudFront distribution cleanup completed"