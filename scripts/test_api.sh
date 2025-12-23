#!/usr/bin/env bash
# Simple script to validate the FastAPI health endpoint using jq.
# Adjust the URL if your backend runs on a different host or port.

API_URL="http://localhost:8000/api/v1/health"

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is not installed."
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is not installed."
  exit 1
fi

echo "Fetching health status from $API_URL ..."
response=$(curl -s -w "%{http_code}" "$API_URL")
http_code="${response: -3}"
body="${response%???}"

if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
  echo "Response ($http_code):"
  echo "$body" | jq .
else
  echo "Failed with HTTP status $http_code"
  echo "Response body:"
  echo "$body"
  exit 1
fi
