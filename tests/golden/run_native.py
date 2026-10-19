"""Run every golden case through the native engine and save the results.
Usage: .venv/bin/python -m tests.golden.run_native [out.json]"""
import json
import sys
import time

from app import api
from tests.golden.cases import cases

out_path = sys.argv[1] if len(sys.argv) > 1 else "tests/golden/out/native.json"
t0 = time.time()
results = {}
for c in cases():
    status, body = api.handle(c["path"], c["query"], c["body"])
    results[c["id"]] = {"status": status, "body": body}
import os
os.makedirs(os.path.dirname(out_path), exist_ok=True)
json.dump({"cases": cases(), "results": results}, open(out_path, "w"), ensure_ascii=False)
bad = [k for k, v in results.items() if v["status"] != 200]
print(f"{len(results)} cases in {time.time() - t0:.1f}s; non-200: {bad}")
if bad and os.environ.get("GITHUB_ACTIONS"):
    for k in bad[:15]:
        print(f"::error title=Native case failed {k}::{json.dumps(results[k]['body'])[:900]}")
sys.exit(1 if bad else 0)
