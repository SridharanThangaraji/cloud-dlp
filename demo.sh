#!/usr/bin/env bash
# Cloud DLP demo - run from project root with backend on port 8000 (or set BASE_URL)
set -e
BASE="${BASE_URL:-http://127.0.0.1:8000}"

echo "=============================================="
echo "  Cloud DLP - API demo"
echo "  Base URL: $BASE"
echo "=============================================="
echo ""

echo "1. Health check"
curl -s "$BASE/health" | head -c 80
echo ""
echo ""

echo "2. Upload a SAFE file (no sensitive data)"
echo "   Content: 'Hello, this is a normal document.'"
echo "Hello, this is a normal document." > /tmp/demo_safe.txt
curl -s -X POST -F "file=@/tmp/demo_safe.txt;type=text/plain" "$BASE/upload"
echo ""
echo ""

echo "3. Upload a BLOCKED file (contains email)"
echo "   Content: 'Contact: alice@example.com'"
echo "Contact: alice@example.com" > /tmp/demo_blocked.txt
curl -s -X POST -F "file=@/tmp/demo_blocked.txt;type=text/plain" "$BASE/upload"
echo ""
echo ""

echo "4. Upload with wrong type (expect 400)"
curl -s -X POST -F "file=@/tmp/demo_safe.txt;type=application/octet-stream" "$BASE/upload"
echo ""
echo ""

echo "5. Audit logs (last entries)"
curl -s "$BASE/logs" | python3 -c "
import sys, json
logs = json.load(sys.stdin)
for e in (logs or [])[-5:]:
    print(f\"  {e.get('filename','?')} | {e.get('status','?')} | {e.get('reason','?')}\")
if not logs:
    print('  (no logs)')
"
echo ""
echo "=============================================="
echo "  Done. For UI: open frontend/index.html"
echo "  in a browser (backend must be on 8000)."
echo "=============================================="
