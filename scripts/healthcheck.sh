#!/bin/bash
# scripts/healthcheck.sh
# Health check script for SPR-BOOT01

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-30}"
RETRIES="${RETRIES:-5}"

echo "🔍 Health check starting..."
echo "   API URL: $API_URL"
echo "   Timeout: ${TIMEOUT}s"
echo "   Max retries: $RETRIES"

# Function to check health endpoint
check_health() {
    local response
    response=$(curl -s -w "%{http_code}" -o /tmp/health_response "$API_URL/health" --max-time "$TIMEOUT" 2>/dev/null || echo "000")
    local status_code="${response: -3}"
    
    if [ "$status_code" = "200" ]; then
        echo "✅ Health check passed (HTTP $status_code)"
        cat /tmp/health_response
        return 0
    else
        echo "❌ Health check failed (HTTP $status_code)"
        return 1
    fi
}

# Retry logic
for i in $(seq 1 "$RETRIES"); do
    echo "   Attempt $i/$RETRIES..."
    
    if check_health; then
        echo "🎉 API is healthy and ready!"
        exit 0
    fi
    
    if [ $i -lt "$RETRIES" ]; then
        echo "   Waiting 5 seconds before retry..."
        sleep 5
    fi
done

echo "💥 Health check failed after $RETRIES attempts"
echo "   API may not be ready or there's a configuration issue"
exit 1 