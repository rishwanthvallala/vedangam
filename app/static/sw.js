// Service worker for the static build. The Python runtime, Swiss Ephemeris, engine and city
// list are cached after the first visit, so later visits start quickly and work offline.
const VERSION = "__BUILD_VERSION__";
const APP_CACHE = `jyotish-app-${VERSION}`;
const RUNTIME_CACHE = "jyotish-runtime";   // survives deploys: Pyodide, wheels, engine, cities
const IMMUTABLE = ["/pyodide/", "/wheels/", "engine.zip", "/data/cities.tsv"];

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== APP_CACHE && k !== RUNTIME_CACHE) await caches.delete(k);
    // drop engine archives from older builds
    const rt = await caches.open(RUNTIME_CACHE);
    for (const req of await rt.keys()) if (req.url.includes("engine.zip") && !req.url.includes(VERSION)) await rt.delete(req);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  e.respondWith((async () => {
    if (IMMUTABLE.some((p) => req.url.includes(p))) {   // cache first
      const cache = await caches.open(RUNTIME_CACHE);
      const hit = await cache.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok) cache.put(req, res.clone());
      return res;
    }
    const cache = await caches.open(APP_CACHE);          // network first
    try {
      const res = await fetch(req);
      if (res.ok) cache.put(req, res.clone());
      return res;
    } catch (_) {
      return (await cache.match(req)) || Response.error();
    }
  })());
});
