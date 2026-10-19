#!/usr/bin/env python3
"""Build the serverless (static) site into dist/.

Everything runs in the visitor's browser: the same Python engine (app/api.py and
app/core/*) is executed by Pyodide in a Web Worker, with the Swiss Ephemeris compiled to
WebAssembly (vendor/wheels/pyswisseph-*-wasm32.whl). The output can be served by any
static host (GitHub Pages, Netlify, Cloudflare Pages, S3, `python -m http.server`).

Usage:  .venv/bin/python tools/build_static.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
DIST = ROOT / "dist"
VENDOR = ROOT / "vendor"
PYODIDE_VERSION = "0.29.5"
PYODIDE_FILES = ["pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip",
                 "pyodide-lock.json"]
PYODIDE_CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"

sys.path.insert(0, str(ROOT))


def download(url: str, dest: Path):
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def vendor_runtime() -> tuple[Path, list[Path]]:
    pyo = VENDOR / f"pyodide-{PYODIDE_VERSION}"
    for name in PYODIDE_FILES:
        download(PYODIDE_CDN + name, pyo / name)
    swe = sorted((VENDOR / "wheels").glob("pyswisseph-*wasm32.whl"))
    if not swe:
        sys.exit("vendor/wheels has no pyswisseph WebAssembly wheel; run tools/build_pyswisseph_wasm.sh")
    return pyo, [swe[-1]]


def engine_zip(dest: Path):
    """The Python engine and its data (no web server code)."""
    include = [APP / "__init__.py", APP / "api.py"]
    include += sorted((APP / "core").glob("*.py"))
    include += sorted((APP / "interpret").rglob("*.py")) + sorted((APP / "interpret").rglob("*.json"))
    include += sorted((APP / "i18n").rglob("*.py")) + sorted((APP / "i18n").rglob("*.json"))
    include += sorted((APP / "data" / "ephe").glob("*.se1"))
    include += [APP / "data" / "tzdb.zip"]
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in include:
            z.write(f, f.relative_to(ROOT).as_posix())


def static_api_snapshots(dest: Path):
    """Endpoints whose answers never change are pre-computed (by the same code) so the page
    can show menus and translations before the engine has finished loading."""
    from app import api
    dest.mkdir(parents=True, exist_ok=True)
    snaps = {"meta.json": api.meta(), "kp-subtable.json": api.kp_subtable(),
             "i18n-te.json": api.i18n("te"), "i18n-en.json": api.i18n("en")}
    for name, data in snaps.items():
        (dest / name).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    print("Vendoring the runtime…")
    pyo, wheels = vendor_runtime()
    if DIST.exists():
        shutil.rmtree(DIST)
    print("Copying the web app…")
    shutil.copytree(APP / "static", DIST / "static", ignore=shutil.ignore_patterns("sw.js", "index.html", ".DS_Store"))
    shutil.copytree(pyo, DIST / "static" / "pyodide")
    (DIST / "static" / "wheels").mkdir()
    for w in wheels:
        shutil.copy2(w, DIST / "static" / "wheels" / w.name)
    (DIST / "static" / "data").mkdir()
    shutil.copy2(APP / "data" / "cities.tsv", DIST / "static" / "data" / "cities.tsv")
    print("Packing the engine…")
    engine_zip(DIST / "static" / "engine.zip")
    static_api_snapshots(DIST / "static" / "api")

    h = hashlib.sha256()
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            h.update(f.relative_to(DIST).as_posix().encode())
            h.update(f.read_bytes())
    version = h.hexdigest()[:12]
    (DIST / "static" / "engine-manifest.json").write_text(json.dumps({
        "version": version, "pyodide": PYODIDE_VERSION, "engine": f"engine.zip?v={version}",
        "wheels": [w.name for w in wheels]}, indent=1))

    index = (APP / "static" / "index.html").read_text(encoding="utf-8")
    index = index.replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
    index = index.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="engine" content="browser">', 1)
    (DIST / "index.html").write_text(index, encoding="utf-8")
    (DIST / "sw.js").write_text((APP / "static" / "sw.js").read_text().replace("__BUILD_VERSION__", version))
    (DIST / ".nojekyll").write_text("")

    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"Built dist/ (version {version}, {total / 1e6:.1f} MB before compression)")
    print("Preview:  .venv/bin/python -m http.server -d dist 8080   →  http://localhost:8080")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # surface the reason as a GitHub annotation
        import os
        import traceback
        traceback.print_exc()
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title=Static build failed::{type(e).__name__}: {e}")
        sys.exit(1)
