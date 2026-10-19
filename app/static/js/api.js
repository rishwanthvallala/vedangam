// API transport. In the static (serverless) build every /api/* call is answered by the
// Python engine running in the browser (Pyodide in a Web Worker, see engine-worker.js);
// with the optional FastAPI server it is an ordinary fetch. Both run app/api.py.
export const MODE = document.querySelector('meta[name="engine"]')?.content === "browser" ? "browser" : "server";

let worker = null, seq = 0, readyResolve, state = { state: MODE === "browser" ? "loading" : "ready" };
const pending = new Map();
const listeners = new Set();
const ready = new Promise((r) => { readyResolve = r; });

export function engineState() { return state; }
export function onEngineStatus(fn) { listeners.add(fn); fn(state); }
function emit(s) { state = s; listeners.forEach((f) => f(s)); }

function startWorker() {
  worker = new Worker(new URL("./engine-worker.js", import.meta.url), { type: "module" });
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.type === "status") {
      emit(m);
      if (m.state === "ready") readyResolve();
      return;
    }
    const p = pending.get(m.id);
    if (!p) return;
    pending.delete(m.id);
    if (m.error) p.reject(new Error(m.error));
    else p.resolve(m.result);
  };
  worker.onerror = (e) => emit({ state: "error", message: e.message || "The calculation engine failed to start." });
}

function callEngine(path, query, body) {
  return new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, path, query, body });
  });
}

// ---------------------------------------------------------------- city search (browser mode)
let cities = null;
const fold = (s) => s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
async function loadCities() {
  if (cities) return cities;
  const txt = await (await fetch(new URL("../data/cities.tsv", import.meta.url))).text();
  cities = txt.split("\n").filter(Boolean).map((line) => {
    const [name, ascii, admin, country, lat, lon, pop, tz] = line.split("\t");
    return { name, ascii, admin, country, lat: +lat, lon: +lon, population: +pop, tz, fa: fold(ascii), fn: fold(name) };
  });
  return cities;
}

/** Same algorithm as app/core/geo.py: exact name matches first, then prefixes, by population. */
async function citySearch(q, limit = 12) {
  q = (q || "").trim();
  if (q.length < 2) return [];
  const parts = q.split(",").map((p) => fold(p.trim()));
  const cityQ = parts[0], rest = parts.slice(1).filter(Boolean);
  const out = [], seen = new Set();
  for (const exact of [true, false]) {
    for (const r of await loadCities()) {
      const ok = exact ? r.fa === cityQ || r.fn === cityQ : r.fa.startsWith(cityQ) || r.fn.startsWith(cityQ);
      if (!ok) continue;
      if (rest.length && !rest.every((p) => fold(r.admin).includes(p) || fold(r.country).includes(p))) continue;
      const key = `${r.ascii}|${r.admin}|${r.country}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ name: r.name, admin: r.admin, country: r.country, lat: r.lat, lon: r.lon, tz: r.tz,
        population: r.population, label: [r.name, r.admin, r.country].filter(Boolean).join(", ") });
      if (out.length >= limit) return out;
    }
  }
  return out;
}

const response = (status, body) => ({ ok: status < 400, status, json: async () => body });

// answers that never change are pre-computed at build time (tools/build_static.py)
const SNAPSHOTS = { "/api/meta": "meta.json", "/api/kp/subtable": "kp-subtable.json",
  "/api/i18n/te": "i18n-te.json", "/api/i18n/en": "i18n-en.json" };

/** fetch()-compatible entry point for every /api/* request. */
export async function apiFetch(url, init = {}) {
  if (MODE === "server") return fetch(url, init);
  const u = new URL(url, location.href);
  const query = Object.fromEntries(u.searchParams.entries());
  const path = u.pathname.slice(u.pathname.indexOf("/api/"));
  if (path === "/api/places") return response(200, await citySearch(query.q));
  if (SNAPSHOTS[path]) {
    const r = await fetch(new URL(`../api/${SNAPSHOTS[path]}`, import.meta.url));
    if (r.ok) return response(200, await r.json());
  }
  const body = init.body ? JSON.parse(init.body) : {};
  await ready;
  const r = await callEngine(path, query, body);
  return response(r.status, r.body);
}

if (MODE === "browser") {
  startWorker();
  // offline support and instant repeat visits
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
    navigator.serviceWorker.register(new URL("../../sw.js", import.meta.url)).catch(() => { /* optional */ });
  }
}
