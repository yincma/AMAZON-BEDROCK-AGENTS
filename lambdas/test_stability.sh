#!/bin/bash
for i in 1 2 3; do 
  echo "测试 $i:"
  curl -X POST 'https://n1s8cxndac.execute-api.us-east-1.amazonaws.com/dev/generate' \
    -H 'Content-Type: application/json' \
    -d "{\"topic\":\"测试$i-AI技术\",\"page_count\":3,\"style\":\"professional\"}" \
    --max-time 60 -s | jq -r '.presentation_id // .error // .message' 
  sleep 2
done
