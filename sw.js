// ── Service worker ───────────────────────────────────────────
// Purpose: the app must not die because a CDN is unreachable. mqtt.js is
// loaded from unpkg, so without a cache an unpkg outage (or a captive
// portal, or a flaky mobile connection) leaves the UI unable to talk to
// the lamps at all.
//
// Strategy:
//   • the app shell + mqtt.js  → cache-first  (instant load, CDN-proof)
//   • navigations (the HTML)    → network-first with cache fallback, so a
//     pushed update always lands and never strands anyone on a stale build
const CACHE = "ll-v1";
const LIB   = "https://unpkg.com/mqtt/dist/mqtt.min.js";
const SHELL = ["./", "./index.html", "./favicon.svg", "./manifest.json", LIB];

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // Cache entries individually — one failure (e.g. CDN down during
    // install) must not abort the whole worker.
    await Promise.all(SHELL.map(u => c.add(u).catch(() => {})));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;

  // MQTT runs over WebSockets — never intercept those
  if (req.url.startsWith("ws:") || req.url.startsWith("wss:")) return;

  // HTML: network-first so updates are picked up immediately
  if (req.mode === "navigate" || (req.headers.get("accept") || "").includes("text/html")) {
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const c = await caches.open(CACHE);
        c.put("./index.html", fresh.clone()).catch(() => {});
        return fresh;
      } catch (err) {
        return (await caches.match("./index.html")) || Response.error();
      }
    })());
    return;
  }

  // Everything else (mqtt.js, icons, fonts): cache-first, refresh in background
  e.respondWith((async () => {
    const hit = await caches.match(req);
    if (hit) return hit;
    try {
      const fresh = await fetch(req);
      if (fresh.ok || fresh.type === "opaque") {
        const c = await caches.open(CACHE);
        c.put(req, fresh.clone()).catch(() => {});
      }
      return fresh;
    } catch (err) {
      return Response.error();
    }
  })());
});
