#!/usr/bin/env bash
# Build the serverless site and serve it locally at http://localhost:8080
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" tools/build_static.py
exec "$PY" -m http.server -d dist "${PORT:-8080}"
