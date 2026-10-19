// Web Worker that runs the Jyotish Studio Python engine (app/api.py) in Pyodide.
// Same code as the server, with the Swiss Ephemeris compiled to WebAssembly.
import { loadPyodide } from "../pyodide/pyodide.mjs";

const base = new URL("../", import.meta.url);   // .../static/
const status = (state, message, step) => postMessage({ type: "status", state, message, step });
let handle = null;

const boot = (async () => {
  status("loading", "Downloading the calculation engine", 1);
  const manifest = await (await fetch(new URL("engine-manifest.json", base))).json();
  const py = await loadPyodide({ indexURL: new URL("pyodide/", base).href });
  status("loading", "Loading the Swiss Ephemeris", 2);
  await py.loadPackage(manifest.wheels.map((w) => new URL(`wheels/${w}`, base).href), { messageCallback: () => {} });
  status("loading", "Unpacking charts and texts", 3);
  const buf = await (await fetch(new URL(manifest.engine, base))).arrayBuffer();
  py.unpackArchive(buf, "zip", { extractDir: "/engine" });
  py.runPython("import sys; sys.path.insert(0, '/engine')");
  handle = py.pyimport("app.api").handle_json;
  // warm up the heavy imports so the first chart is quick
  handle("/api/meta", "{}", "{}");
  status("ready", "Ready", 4);
})().catch((e) => status("error", String(e && e.message ? e.message : e)));

onmessage = async (e) => {
  const { id, path, query, body } = e.data;
  try {
    await boot;
    if (!handle) throw new Error("The calculation engine could not be loaded.");
    const out = handle(path, JSON.stringify(query || {}), JSON.stringify(body || {}));
    postMessage({ id, result: JSON.parse(out) });
  } catch (err) {
    postMessage({ id, error: String(err && err.message ? err.message : err) });
  }
};
