/* SafeCycle — basic offline app shell.
   Cache-first for the static shell so the app opens instantly and
   works offline at a basic level. API calls are never cached. */

const CACHE = "safecycle-shell-v2";

const SHELL = [
  "./",
  "./index.html",
  "./css/tokens.css",
  "./css/base.css",
  "./css/components.css",
  "./js/app.js",
  "./js/router.js",
  "./js/state.js",
  "./js/api.js",
  "./js/data/products.js",
  "./js/data/questions.js",
  "./manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Never cache API traffic (privacy + freshness).
  if (request.url.includes("/api/")) {
    return; // fall through to network
  }

  // Cache-first for same-origin GETs.
  if (request.method === "GET" && new URL(request.url).origin === self.location.origin) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((resp) => {
            const copy = resp.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
            return resp;
          }).catch(() => cached)
      )
    );
  }
});
