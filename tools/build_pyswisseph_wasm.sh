#!/usr/bin/env bash
# Rebuild the Swiss Ephemeris Python binding (pyswisseph) as a Pyodide/WebAssembly wheel.
# Only needed when upgrading Pyodide or pyswisseph; the result is committed in vendor/wheels/.
set -euo pipefail
PYODIDE_VERSION="${PYODIDE_VERSION:-0.29.5}"
PYSWISSEPH_VERSION="${PYSWISSEPH_VERSION:-2.10.3.2}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
python3.13 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q pyodide-build
"$WORK/venv/bin/pyodide" xbuildenv install "$PYODIDE_VERSION"
"$WORK/venv/bin/pyodide" xbuildenv install-emscripten
EMSDK_ENV="$(dirname "$("$WORK/venv/bin/pyodide" config get xbuildenv_path)")/emsdk/emsdk_env.sh"
"$WORK/venv/bin/pip" download -q --no-binary :all: --no-deps "pyswisseph==$PYSWISSEPH_VERSION" -d "$WORK/src"
tar -xzf "$WORK/src/pyswisseph-$PYSWISSEPH_VERSION.tar.gz" -C "$WORK/src"
cd "$WORK/src/pyswisseph-$PYSWISSEPH_VERSION"
# The optional sqlite-based atlas helper is not used by the app and doesn't cross-compile.
sed -i.bak 's/^use_swephelp = True/use_swephelp = False/; s/^swe_detection = True/swe_detection = False/' setup.py
# shellcheck disable=SC1090
source "$EMSDK_ENV" >/dev/null
"$WORK/venv/bin/pyodide" build
cp dist/*.whl "$ROOT/vendor/wheels/"
echo "Built: $(ls dist/*.whl)"
