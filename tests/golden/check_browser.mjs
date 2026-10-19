// Runs every golden case through the in-browser engine exactly as the static site does
// (Pyodide + WebAssembly Swiss Ephemeris + engine.zip from dist/) and compares the output
// with the native engine's results, field by field.
//
// Usage: node tests/golden/check_browser.mjs [native.json] [dist dir]
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const nativePath = process.argv[2] || "tests/golden/out/native.json";
const dist = path.resolve(process.argv[3] || "dist");
const staticDir = path.join(dist, "static");
const { loadPyodide } = await import(pathToFileURL(path.join(staticDir, "pyodide", "pyodide.mjs")).href);

const t0 = Date.now();
const py = await loadPyodide({ indexURL: path.join(staticDir, "pyodide") + path.sep });
const manifest = JSON.parse(fs.readFileSync(path.join(staticDir, "engine-manifest.json")));
await py.loadPackage(manifest.wheels.map((w) => path.join(staticDir, "wheels", w)), { messageCallback: () => {} });
py.unpackArchive(new Uint8Array(fs.readFileSync(path.join(staticDir, "engine.zip"))), "zip", { extractDir: "/engine" });
py.runPython("import sys; sys.path.insert(0, '/engine')");
const handle = py.pyimport("app.api").handle_json;
console.log(`engine loaded in ${((Date.now() - t0) / 1000).toFixed(1)}s`);

const { cases, results } = JSON.parse(fs.readFileSync(nativePath, "utf8"));
// Absolute tolerance. 1e-5 of a degree is 0.036 arc-seconds (≈ 0.1 s of ascendant motion);
// set GOLDEN_TOL=0 to demand bit-for-bit equality.
const TOL = Number(process.env.GOLDEN_TOL ?? 1e-5);

function diff(a, b, p, out) {
  if (out.length > 5) return;
  if (typeof a === "number" && typeof b === "number") {
    if (Math.abs(a - b) > TOL) out.push(`${p}: native ${a} vs browser ${b}`);
    return;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) { out.push(`${p}: length ${a.length} vs ${b.length}`); return; }
    a.forEach((x, i) => diff(x, b[i], `${p}[${i}]`, out));
    return;
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
    if (ka.join() !== kb.join()) { out.push(`${p}: keys differ`); return; }
    for (const k of ka) diff(a[k], b[k], `${p}.${k}`, out);
    return;
  }
  if (a !== b) out.push(`${p}: native ${JSON.stringify(a)?.slice(0, 80)} vs browser ${JSON.stringify(b)?.slice(0, 80)}`);
}

let pass = 0, fail = 0;
const t1 = Date.now();
for (const c of cases) {
  const got = JSON.parse(handle(c.path, JSON.stringify(c.query), JSON.stringify(c.body)));
  const want = results[c.id];
  const out = [];
  if (got.status !== want.status) out.push(`status ${want.status} vs ${got.status}: ${JSON.stringify(got.body).slice(0, 200)}`);
  else diff(want.body, got.body, "", out);
  if (out.length) { fail++; console.log(`FAIL ${c.id}\n   ${out.join("\n   ")}`); } else pass++;
}
console.log(`\n${pass} identical, ${fail} different, out of ${cases.length} cases (${((Date.now() - t1) / 1000).toFixed(1)}s)`);
process.exit(fail ? 1 : 0);
