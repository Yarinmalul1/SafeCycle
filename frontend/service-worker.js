/* SafeCycle — SELF-DESTROYING service worker (dev kill switch).
   The previous versions cached the app shell, which kept serving stale
   files during development. This worker takes over, deletes all caches,
   unregisters itself, and reloads any open tab from the network.
   Result: after one visit, no service worker remains and content is fresh.
   (Re-introduce a caching worker for production PWA/offline later.) */

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // Wipe every cache this origin holds.
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      // Remove this worker.
      await self.registration.unregister();
      // Reload controlled tabs so they fetch fresh from the network.
      const clients = await self.clients.matchAll({ type: "window" });
      clients.forEach((client) => client.navigate(client.url));
    })()
  );
});

// Pass everything straight to the network (no caching).
self.addEventListener("fetch", () => {});
