#!/usr/bin/env bash
# Build the serverless site and prove it computes exactly what the native engine computes.
#   1. build dist/        2. run 377 golden cases natively        3. run them in Pyodide/WASM and compare
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" tools/build_static.py
"$PY" -m tests.golden.run_native tests/golden/out/native.json
node tests/golden/check_browser.mjs tests/golden/out/native.json dist
