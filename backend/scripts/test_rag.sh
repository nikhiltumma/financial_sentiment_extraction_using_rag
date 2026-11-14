#!/bin/bash
# Test the full RAG pipeline from your machine
# Requires: Gemini API key in .env, backend running on port 8000

set -e

BACKEND="http://localhost:8000"

echo "=== 1. Health check ==="
curl -s "$BACKEND/health" | python3 -m json.tool 2>/dev/null || curl -s "$BACKEND/health"

echo ""
echo "=== 2. Analysis text (no Gemini needed) ==="
curl -s -X POST "$BACKEND/analysis/text" \
  -H "Content-Type: application/json" \
  -d '{"text":"Surya Technologies reported Q3 semiconductor shipments of 4.2 million units, up 12% against consensus.","content_type":"news","language":"en"}' \
  | python3 -m json.tool 2>/dev/null || curl -s -X POST "$BACKEND/analysis/text" \
  -H "Content-Type: application/json" \
  -d '{"text":"Surya Technologies reported Q3 semiconductor shipments of 4.2 million units, up 12% against consensus.","content_type":"news","language":"en"}'

echo ""
echo "=== 3. Graph generate (needs Gemini) ==="
GRAPH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BACKEND/graph/generate" \
  -H "Content-Type: application/json" \
  -d '{"documents":[{"text":"Surya Technologies Limited reported Q3 semiconductor shipments of 4.2 million units, up 12% against the consensus estimate of 3.75 million, driven by a recovery in automotive electronics orders.","document_id":"doc1","source_name":"test","language":"en"}]}')

HTTP_CODE=$(echo "$GRAPH_RESPONSE" | tail -1)
BODY=$(echo "$GRAPH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "Graph generated successfully:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo "Graph generate failed (HTTP $HTTP_CODE):"
    echo "$BODY" | head -20
    echo ""
    echo "NOTE: If this times out, your network may block Gemini POST requests."
    echo "The key works (GET /models returns 200) but POST generateContent hangs."
    echo "Try from a different network or check firewall/proxy settings."
fi

echo ""
echo "=== 4. Index status ==="
curl -s "$BACKEND/analysis/index/status" | python3 -m json.tool 2>/dev/null || curl -s "$BACKEND/analysis/index/status"

echo ""
echo "=== 5. Build index (if graphs exist) ==="
curl -s -X POST "$BACKEND/analysis/index/build" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool 2>/dev/null || curl -s -X POST "$BACKEND/analysis/index/build" \
  -H "Content-Type: application/json"

echo ""
echo "=== 6. RAG query (needs FAISS index + Gemini) ==="
curl -s -X POST "$BACKEND/analysis/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"Surya Technologies Q3 shipments","top_k":3}' \
  | python3 -m json.tool 2>/dev/null || curl -s -X POST "$BACKEND/analysis/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"Surya Technologies Q3 shipments","top_k":3}'
