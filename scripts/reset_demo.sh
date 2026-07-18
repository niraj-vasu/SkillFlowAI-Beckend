#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true

echo "Resetting demo data..."
curl -s -X POST http://127.0.0.1:8000/api/demo/reset | python3 -m json.tool
echo "Demo data reset complete."
